import os
import random
import string
import subprocess
import time
import socket
import json
import threading
import asyncio
import io
import zipfile
import base64
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import quote
import httpx
import websockets

# Initialize FastAPI app
app = FastAPI()
templates = Jinja2Templates(directory="/tmp/templates")

# Set up application logging
import logging
logger = logging.getLogger("session_manager")
logger.setLevel(logging.DEBUG)
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "5"))
INACTIVITY_TIMEOUT = int(os.environ.get("INACTIVITY_TIMEOUT", "3600"))

# Track last activity per session to avoid killing active sessions
LAST_ACTIVITY = {}
ACTIVITY_LOCK = threading.Lock()

# Track active WebSocket connections per session
ACTIVE_WEBSOCKETS = {}
WEBSOCKET_LOCK = threading.Lock()

def mark_activity(session_id: str):
    try:
        with ACTIVITY_LOCK:
            LAST_ACTIVITY[session_id] = time.time()
            logger.debug(f"Activity marked for session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to mark activity for session {session_id}: {e}")

def add_websocket_connection(session_id: str, websocket_id: str):
    """Track a new WebSocket connection for a session"""
    try:
        with WEBSOCKET_LOCK:
            if session_id not in ACTIVE_WEBSOCKETS:
                ACTIVE_WEBSOCKETS[session_id] = set()
            ACTIVE_WEBSOCKETS[session_id].add(websocket_id)
            logger.debug(f"Added WebSocket {websocket_id} for session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to add WebSocket for session {session_id}: {e}")

def remove_websocket_connection(session_id: str, websocket_id: str):
    """Remove a WebSocket connection and check if session should be terminated"""
    try:
        with WEBSOCKET_LOCK:
            if session_id in ACTIVE_WEBSOCKETS:
                ACTIVE_WEBSOCKETS[session_id].discard(websocket_id)
                logger.debug(f"Removed WebSocket {websocket_id} for session {session_id}")
                
                # If no more WebSocket connections, schedule termination check
                if not ACTIVE_WEBSOCKETS[session_id]:
                    del ACTIVE_WEBSOCKETS[session_id]
                    logger.info(f"No active WebSockets for session {session_id}, scheduling termination check")
                    # Schedule container termination check with delay to handle reconnections
                    threading.Thread(target=delayed_termination_check, args=(session_id,), daemon=True).start()
    except Exception as e:
        logger.warning(f"Failed to remove WebSocket for session {session_id}: {e}")

def delayed_termination_check(session_id: str):
    """Wait a bit and check if session should be terminated (handles reconnections)"""
    # Wait 5 seconds to allow for reconnections (VS Code often reconnects quickly)
    time.sleep(5)
    
    try:
        with WEBSOCKET_LOCK:
            # Check if new connections were established during the delay
            if session_id not in ACTIVE_WEBSOCKETS or not ACTIVE_WEBSOCKETS[session_id]:
                logger.info(f"No reconnection detected for session {session_id}, terminating container")
                terminate_session_container(session_id)
            else:
                logger.debug(f"Session {session_id} reconnected, canceling termination")
    except Exception as e:
        logger.error(f"Failed to check termination for session {session_id}: {e}")

def terminate_session_container(session_id: str):
    """Terminate a session container immediately"""
    try:
        container_name = f"kotorscript-{session_id}"
        logger.info(f"Terminating container {container_name} due to client disconnect")
        kill_container(container_name)
        
        # Clean up tracking data
        with ACTIVITY_LOCK:
            LAST_ACTIVITY.pop(session_id, None)
        with WEBSOCKET_LOCK:
            ACTIVE_WEBSOCKETS.pop(session_id, None)
            
    except Exception as e:
        logger.error(f"Failed to terminate container for session {session_id}: {e}")

async def handle_websocket_proxy(websocket: WebSocket, upstream, session_id: str):
    """Handle bidirectional WebSocket proxying between client and upstream"""
    async def client_to_upstream():
        try:
            while True:
                message = await websocket.receive()
                data = message.get("bytes") if message.get("bytes") is not None else message.get("text")
                if data is None:
                    continue
                # mark activity on client message
                mark_activity(session_id)
                await upstream.send(data)
        except Exception:
            pass

    async def upstream_to_client():
        try:
            async for msg in upstream:
                # mark activity on upstream message
                mark_activity(session_id)
                if isinstance(msg, bytes):
                    await websocket.send_bytes(msg)
                else:
                    await websocket.send_text(msg)
        except Exception:
            pass

    await asyncio.gather(client_to_upstream(), upstream_to_client())

def get_network_name(partial_name):
    output = subprocess.check_output(["docker", "network", "ls", "--format", "{{.Name}}"])
    networks = output.decode().splitlines()
    logger.debug(f"Found {len(networks)} docker networks: {networks}")
    for net in networks:
        if partial_name in net:
            logger.info(f"Using docker network: {net}")
            return net
    logger.warning(f"No network found matching '{partial_name}', will use default")
    return None

def wait_for_port(host, port, timeout=30.0):
    """Wait until a TCP port is open on the given host."""
    logger.debug(f"Waiting for {host}:{port} to be ready (timeout: {timeout}s)")
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                elapsed = time.time() - start
                logger.info(f"Port {host}:{port} ready after {elapsed:.1f}s")
                return True
        except Exception:
            time.sleep(0.5)
    logger.error(f"Timeout waiting for {host}:{port} after {timeout}s")
    return False

def get_mapped_host_port(container_name, container_port="3000/tcp"):
    """Return the host port mapped to container_port for a container."""
    try:
        inspect_raw = subprocess.check_output(["docker", "inspect", container_name])
        data = json.loads(inspect_raw)[0]
        ports = data.get("NetworkSettings", {}).get("Ports", {})
        bindings = ports.get(container_port)
        if bindings and len(bindings) > 0:
            host_port = bindings[0].get("HostPort")
            if host_port:
                return int(host_port)
    except Exception:
        pass
    return None

def list_running_session_containers():
    try:
        output = subprocess.check_output([
            "docker", "ps", "-q", "-f", "name=^/kotorscript-"
        ])
        ids = output.decode().split()
        logger.debug(f"Found {len(ids)} running session containers: {ids}")
        return ids
    except Exception as e:
        logger.error(f"Failed to list running containers: {e}")
        return []

def count_running_sessions():
    count = len(list_running_session_containers())
    logger.debug(f"Current session count: {count}/{MAX_SESSIONS}")
    return count

def kill_container(container_name_or_id):
    try:
        logger.info(f"Killing container: {container_name_or_id}")
        subprocess.run(["docker", "rm", "-f", container_name_or_id], check=True)
        logger.info(f"Successfully killed container: {container_name_or_id}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to kill container {container_name_or_id}: {e}")
        return False

def parse_docker_time(ts):
    # Docker format examples: '2025-09-07T10:16:19.123456789Z' or '2025-09-07T10:16:19Z'
    if ts.endswith("Z"):
        ts = ts[:-1]
    # Trim nanoseconds to microseconds for Python
    if "." in ts:
        date_part, frac = ts.split(".", 1)
        frac = (frac + "000000")[:6]
        ts = f"{date_part}.{frac}"
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def cleanup_stale_sessions():
    try:
        # Use a timeout for docker commands to avoid blocking
        def run_docker_cmd(cmd: list[str], timeout: float = 5) -> bytes:
            try:
                return subprocess.check_output(cmd, timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.error(f"Docker command timed out: {' '.join(cmd)}")
                return b""
            except Exception as e:
                logger.error(f"Docker command failed: {' '.join(cmd)}: {e}")
                return b""

        output = run_docker_cmd([
            "docker", "ps", "-a", "--filter", "name=^/kotorscript-", "--format", "{{.ID}}"
        ])
        ids = output.decode().split()
        logger.debug(f"Checking {len(ids)} containers for stale sessions (timeout: {INACTIVITY_TIMEOUT}s)")

        stale_count = 0

        # To avoid blocking, inspect containers in parallel using threads
        import concurrent.futures

        def check_and_cleanup(cid):
            try:
                inspect_raw = run_docker_cmd(["docker", "inspect", cid])
                if not inspect_raw:
                    return 0
                data = json.loads(inspect_raw)[0]
                # Determine session_id from container name
                cname = (data.get("Name") or "").lstrip("/")
                sid = cname.replace("kotorscript-", "") if cname.startswith("kotorscript-") else None
                # Use last activity if known, else fall back to start time
                last_activity_ts = None
                if sid:
                    with ACTIVITY_LOCK:
                        last_activity_ts = LAST_ACTIVITY.get(sid)
                if last_activity_ts is None:
                    started_at = data.get("State", {}).get("StartedAt") or data.get("Created")
                    if started_at:
                        started_dt = parse_docker_time(started_at)
                        last_activity_ts = started_dt.timestamp()
                if last_activity_ts is not None:
                    age_sec = time.time() - last_activity_ts
                    if age_sec > INACTIVITY_TIMEOUT:
                        logger.info(f"Session {sid} inactive for {age_sec:.0f}s, cleaning up")
                        kill_container(cid)
                        return 1
                    else:
                        logger.debug(f"Session {sid} active ({age_sec:.0f}s ago)")
                return 0
            except Exception as e:
                logger.warning(f"Error checking container {cid}: {e.__class__.__name__}: {e}")
                return 0

        # Use a thread pool to parallelize container inspection/cleanup
        max_workers = min(8, len(ids)) if ids else 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks and wait with timeout to avoid blocking indefinitely
            futures = [executor.submit(check_and_cleanup, cid) for cid in ids]
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=15):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.warning(f"Container cleanup task failed: {e.__class__.__name__}: {e}")
                    results.append(0)
            stale_count = sum(results)

        if stale_count > 0:
            logger.info(f"Cleaned up {stale_count} stale sessions")
    except Exception as e:
        logger.error(f"Failed to cleanup stale sessions: {e.__class__.__name__}: {e}")

def cleanup_orphaned_containers_sync():
    """Synchronous version of cleanup for startup"""
    cleaned = 0
    try:
        running_containers = list_running_session_containers()
        
        with WEBSOCKET_LOCK:
            for container_id in running_containers:
                # Get container name to extract session ID
                try:
                    inspect_raw = subprocess.check_output(["docker", "inspect", container_id])
                    data = json.loads(inspect_raw)[0]
                    container_name = (data.get("Name") or "").lstrip("/")
                    
                    if container_name.startswith("kotorscript-"):
                        session_id = container_name.replace("kotorscript-", "")
                        
                        # On startup, all containers are orphaned since we have no active connections
                        logger.info(f"Cleaning up orphaned container for session {session_id} on startup")
                        kill_container(container_id)
                        cleaned += 1
                        
                        # Clean up tracking data
                        with ACTIVITY_LOCK:
                            LAST_ACTIVITY.pop(session_id, None)
                        ACTIVE_WEBSOCKETS.pop(session_id, None)
                        
                except Exception as e:
                    logger.warning(f"Failed to inspect container {container_id}: {e.__class__.__name__}: {e}")
                    continue
                    
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} orphaned containers on startup")
        else:
            logger.info("No orphaned containers found on startup")
            
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned containers on startup: {e.__class__.__name__}: {e}")

def start_reaper_thread():
    def loop():
        logger.info("Session reaper thread started")
        while True:
            cleanup_stale_sessions()
            time.sleep(30)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    logger.info("Started session cleanup reaper thread (30s interval)")

async def proxy_http(request: Request, session_id: str, tail: str):
    # Preserve original subpath (/s/{session_id}/...) as base-path expected by backend
    path = request.url.path
    query = ("?" + request.url.query) if request.url.query else ""
    target = f"http://kotorscript-{session_id}:3000{path}{query}"
    logger.debug(f"Proxying HTTP {request.method} {path}{query} to {target} for session {session_id}")
    # mark activity for this session
    mark_activity(session_id)
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()
    async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
        resp = await client.request(request.method, target, headers=headers, content=body)
        excluded = {"content-encoding", "transfer-encoding", "connection"}
        response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded]
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(response_headers))

async def proxy_ws(websocket: WebSocket, session_id: str, tail: str):
    # Forward the full original path and query so base-path works and tokens are preserved
    ws_path = websocket.url.path
    ws_query = ("?" + websocket.url.query) if websocket.url.query else ""
    target = f"ws://kotorscript-{session_id}:3000{ws_path}{ws_query}"
    logger.info(f"WebSocket connection to {target} for session {session_id}")
    
    # Generate unique WebSocket ID for tracking
    websocket_id = f"{session_id}-{id(websocket)}"
    
    # Prepare headers and subprotocols for upstream handshake
    extra_headers = []
    cookie = websocket.headers.get("cookie")
    if cookie:
        extra_headers.append(("Cookie", cookie))
    user_agent = websocket.headers.get("user-agent")
    if user_agent:
        extra_headers.append(("User-Agent", user_agent))
    # Preserve client Origin if present to avoid origin-related disconnects
    origin_hdr = websocket.headers.get("origin")
    # Pass through subprotocols if present
    subprotocols = None
    sec_ws_proto = websocket.headers.get("sec-websocket-protocol")
    if sec_ws_proto:
        subprotocols = [p.strip() for p in sec_ws_proto.split(',') if p.strip()]
        logger.debug(f"WebSocket subprotocols: {subprotocols}")
    # Accept client websocket, mirroring subprotocol if provided
    selected_subprotocol = subprotocols[0] if subprotocols else None
    # mark activity on connect and track the WebSocket
    mark_activity(session_id)
    add_websocket_connection(session_id, websocket_id)
    await websocket.accept(subprotocol=selected_subprotocol)
    try:
        # Create connection kwargs with basic parameters
        connect_kwargs = {
            "max_size": None,
        }
        
        # Add subprotocols if present
        if subprotocols:
            connect_kwargs["subprotocols"] = subprotocols
            
        # Add origin if present
        if origin_hdr:
            connect_kwargs["origin"] = origin_hdr
            
        # Try to add extra headers, but handle the case where it's not supported
        try:
            if extra_headers:
                connect_kwargs["extra_headers"] = extra_headers
            async with websockets.connect(target, **connect_kwargs) as upstream:
                await handle_websocket_proxy(websocket, upstream, session_id)
        except TypeError as e:
            if "extra_headers" in str(e):
                # Retry without extra_headers if that parameter is not supported
                logger.warning(f"WebSocket library doesn't support extra_headers, retrying without them for session {session_id}")
                connect_kwargs.pop("extra_headers", None)
                async with websockets.connect(target, **connect_kwargs) as upstream:
                    await handle_websocket_proxy(websocket, upstream, session_id)
            else:
                raise
    except Exception as e:
        logger.error(f"WebSocket proxy error for session {session_id}: {e}")
        await asyncio.sleep(0)
    finally:
        logger.debug(f"WebSocket connection closed for session {session_id}")
        # Remove WebSocket connection tracking and potentially terminate container
        remove_websocket_connection(session_id, websocket_id)
        try:
            await websocket.close()
        except Exception:
            pass

@app.get("/health")
async def health():
    return Response(content="OK", status_code=200, media_type="text/plain")

@app.post("/cleanup-orphaned")
async def cleanup_orphaned_containers():
    """Manually cleanup containers that have no active WebSocket connections"""
    cleaned = 0
    try:
        running_containers = list_running_session_containers()
        
        with WEBSOCKET_LOCK:
            for container_id in running_containers:
                # Get container name to extract session ID
                try:
                    inspect_raw = subprocess.check_output(["docker", "inspect", container_id])
                    data = json.loads(inspect_raw)[0]
                    container_name = (data.get("Name") or "").lstrip("/")
                    
                    if container_name.startswith("kotorscript-"):
                        session_id = container_name.replace("kotorscript-", "")
                        
                        # Check if this session has any active WebSocket connections
                        if session_id not in ACTIVE_WEBSOCKETS or not ACTIVE_WEBSOCKETS[session_id]:
                            logger.info(f"Cleaning up orphaned container for session {session_id}")
                            kill_container(container_id)
                            cleaned += 1
                            
                            # Clean up tracking data
                            with ACTIVITY_LOCK:
                                LAST_ACTIVITY.pop(session_id, None)
                            ACTIVE_WEBSOCKETS.pop(session_id, None)
                            
                except Exception as e:
                    logger.warning(f"Failed to inspect container {container_id}: {e.__class__.__name__}: {e}")
                    continue
                    
        return JSONResponse({"cleaned": cleaned, "message": f"Cleaned up {cleaned} orphaned containers"})
        
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned containers: {e.__class__.__name__}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/capacity")
async def capacity():
    cleanup_stale_sessions()
    current = count_running_sessions()
    return JSONResponse({"current": current, "max": MAX_SESSIONS, "available": current < MAX_SESSIONS})

@app.api_route("/new", methods=["GET", "POST"])
async def new_session(request: Request):
    import glob

    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"New session request from {client_ip}")
    
    # Clean up any stale sessions first
    cleanup_stale_sessions()

    # If user has an existing session cookie, kill that container (allow replacement)
    old_sid = request.cookies.get("ksid") if hasattr(request, 'cookies') else request.headers.get('cookie','').replace('ksid=','')
    if old_sid:
        logger.info(f"Replacing existing session {old_sid} from {client_ip}")
        kill_container(f"kotorscript-{old_sid}")

    # Enforce session limit with waiting room page (after possible self-replacement)
    current_sessions = count_running_sessions()
    if current_sessions >= MAX_SESSIONS:
        logger.warning(f"Session limit reached ({current_sessions}/{MAX_SESSIONS}), showing waiting room to {client_ip}")
        
        # Render waiting room template
        return templates.TemplateResponse(
            "waiting.html",
            {
                "request": request,
                "current": current_sessions,
                "max": MAX_SESSIONS,
                "year": datetime.now().year
            }
        )

    session_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    container_name = f"kotorscript-{session_id}"
    connection_token = "".join(random.choices(string.ascii_letters + string.digits, k=24))
    network_name = get_network_name(os.environ.get("NETWORK_NAME", "publicnet")) or "bridge"
    default_workspace = os.environ.get("DEFAULT_WORKSPACE", "/workspace")
    ext_path = os.environ.get("EXT_PATH", "")

    # Set openvscode globally based on environment variable or default
    openvscode = os.environ.get("OPENVSCODE", "1").lower() in ("1", "true", "yes")
    
    logger.info(f"Creating session {session_id} for {client_ip} (openvscode: {openvscode})")

    DOCKER_MEMORY_LIMIT = os.environ.get("SESSION_MEMORY_LIMIT", "2048m")  # 2GB per container
    DOCKER_CPU_LIMIT = os.environ.get("SESSION_CPU_LIMIT", "0.75")          # 0.75 CPU (75% of a core) per container

    try:
        # Start container without exposing ports; we'll reverse-proxy internally
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "--network", network_name,
            "-l", "com.bolabaden.kotorscript=1",
            "--memory", DOCKER_MEMORY_LIMIT,
            "--cpus", DOCKER_CPU_LIMIT,
        ]

        if openvscode:
            cmd.extend([
                "-e", f"OPENVSCODE_SERVER_CONNECTION_TOKEN={connection_token}",
                "-e", f"HOME=/workspace",
                "-v", f"{ext_path}:{ext_path}:ro",
                "--tmpfs", f"/workspace:rw,size=64M,mode=1777",
                "--tmpfs", "/config:rw,size=16M,mode=1777",
                "gitpod/openvscode-server:latest",
                "--server-base-path", f"/s/{session_id}"
            ])
        else:
            # code-server setup
            cmd.extend([
                "lscr.io/linuxserver/code-server:latest"
            ])

        logger.debug(f"Starting container with command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        logger.info(f"Container {container_name} started successfully")
        print("Installing extension", ext_path)
        ext_install_cmd = [
            "docker",
            "exec",
            container_name,
            "/home/.openvscode-server/bin/openvscode-server",
            "--install-extension",
            f"{ext_path}"
        ]
        print("Command: ", [' '.join(ext_install_cmd)])
        subprocess.run(
            ext_install_cmd,
            check=True
        )
        print("Extension installed")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start container {container_name}: {e}")
        return Response(content=f"Failed to start container: {e}", status_code=500)

    # Wait until the container port is reachable on the Docker network
    port = 3000 if openvscode else 8443
    if not wait_for_port(container_name, port, timeout=60):
        logger.error(f"Session {session_id} failed to start within timeout, cleaning up")
        subprocess.run(["docker", "rm", "-f", container_name], check=True)
        return Response(content="Session failed to start in time.", status_code=500)

    # Redirect browser to proxied path handled by Traefik
    forwarded_host = (request.headers.get("X-Forwarded-Host") or request.url.hostname or "").split(",")[0].strip()
    scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme or "https")
    # Auto-load workspace folder to avoid "open folder" dialog
    flags=f"?tkn={connection_token}&" if openvscode else "?"
    redirect_url = f"{scheme}://{forwarded_host}/s/{session_id}/{flags}folder={quote(default_workspace)}"
    
    logger.info(f"Session {session_id} ready, redirecting {client_ip} to {redirect_url}")
    resp = RedirectResponse(redirect_url, status_code=302)
    # initialize last activity now
    mark_activity(session_id)
    resp.set_cookie("ksid", session_id, max_age=INACTIVITY_TIMEOUT, httponly=True)
    return resp

@app.get("/")
async def index(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    # Do NOT kill existing session on refresh; just render lobby
    sid = request.cookies.get("ksid") if hasattr(request, 'cookies') else None
    
    # Get current session count
    current = count_running_sessions()
    available = current < MAX_SESSIONS
    
    logger.debug(f"Index page request from {client_ip} (sessions: {current}/{MAX_SESSIONS}, has_cookie: {sid is not None})")
    
    # Render template
    response = templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "current": current,
            "max": MAX_SESSIONS,
            "available": available,
            "year": datetime.now().year
        }
    )
    
    # Clear session cookie if needed
    if sid:
        response.delete_cookie("ksid")
        
    return response

# Workspace download endpoint
@app.get("/s/{session_id}/download-workspace")
async def download_workspace(session_id: str):
    container_name = f"kotorscript-{session_id}"
    logger.info(f"Workspace download requested for session {session_id}")
    
    # Check if container exists
    try:
        output = subprocess.check_output(["docker", "inspect", container_name], stderr=subprocess.DEVNULL)
        container_data = json.loads(output)[0]
        if container_data.get("State", {}).get("Status") != "running":
            logger.warning(f"Download requested for non-running session {session_id}")
            return JSONResponse({"error": "Session not running"}, status_code=404)
    except subprocess.CalledProcessError:
        logger.warning(f"Download requested for non-existent session {session_id}")
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    # Create a temporary directory for the workspace
    temp_dir = f"/tmp/workspace-{session_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Execute command to export workspace files from container
            cmd = ["docker", "exec", container_name, "find", "/workspace", "-type", "f", "-not", "-path", "*/\\.*"]
            files_output = subprocess.check_output(cmd).decode().strip().split('\n')
            
            file_count = 0
            for file_path in files_output:
                if not file_path:  # Skip empty lines
                    continue
                    
                # Get file content from container
                try:
                    content = subprocess.check_output(["docker", "exec", container_name, "cat", file_path])
                    # Add file to zip (removing /workspace prefix)
                    zip_file.writestr(file_path.replace('/workspace/', ''), content)
                    file_count += 1
                except subprocess.CalledProcessError:
                    continue  # Skip files that can't be read
        
        # Reset buffer position
        zip_buffer.seek(0)
        
        logger.info(f"Created workspace download for session {session_id} with {file_count} files")
        
        # Return the zip file
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=workspace-{session_id}.zip"}
        )
    except Exception as e:
        logger.error(f"Failed to create workspace download for session {session_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# HTTP proxy routes: /s/{session_id}/... and WebSocket
@app.api_route("/s/{session_id}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
@app.api_route("/s/{session_id}/{tail:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def http_proxy_route(session_id: str, tail: str = "", request: Request = None):
    # Skip proxying for our custom download endpoint
    if tail == "download-workspace":
        return await download_workspace(session_id)
    return await proxy_http(request, session_id, tail)

@app.websocket("/s/{session_id}")
@app.websocket("/s/{session_id}/{tail:path}")
async def ws_proxy_route(session_id: str, tail: str = "", websocket: WebSocket = None):
    await proxy_ws(websocket, session_id, tail)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Log startup configuration
    port = int(os.environ.get("SESSION_MANAGER_PORT", 8080))
    logger.info(f"Starting Session Manager on port {port}")
    logger.info(f"Configuration: MAX_SESSIONS={MAX_SESSIONS}, INACTIVITY_TIMEOUT={INACTIVITY_TIMEOUT}s")
    logger.info(f"Default workspace: {os.environ.get('DEFAULT_WORKSPACE', '/workspace')}")
    logger.info(f"OpenVSCode mode: {os.environ.get('OPENVSCODE', '1')}")
    
    # Clean up any orphaned containers from previous runs
    cleanup_orphaned_containers_sync()
    
    start_reaper_thread()
    import uvicorn
    
    # Check if custom log config exists
    log_config = None
    if os.path.exists("logging_config.json"):
        log_config = "logging_config.json"
        logger.info("Using custom logging configuration")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="trace",  # Most verbose level
        use_colors=True,  # Enable colored output
    )