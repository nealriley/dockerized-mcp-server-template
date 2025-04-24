import os
import multiprocessing
import uvicorn
from mcp.server.fastmcp import FastMCP
import yaml, requests, uuid
import logging
import traceback
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("docker-mcp")
logger.info("Starting dockerized MCP server initialization")

try:
    logger.info("Initializing FastMCP instance")
    mcp = FastMCP("docker-mcp")
    app = mcp.sse_app()
    logger.info("FastMCP instance and SSE app successfully created")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)

TOOL_PREFIX = os.getenv("TOOL_PREFIX", "tool")
logger.info(f"Using tool prefix: {TOOL_PREFIX}")

# Determine where to load/save the OpenAPI spec
download_url = os.getenv("OPENAPI_SPEC_URL")
local_spec = os.path.join(os.path.dirname(__file__), "openapi.v2.yaml")
logger.info(f"Download URL: {download_url}, Local spec path: {local_spec}")

try:
    if download_url:
        # write into a writable temp location
        spec_path = os.path.join("/tmp", "openapi.v2.yaml")
        logger.info(f"Creating directory for downloaded spec at {os.path.dirname(spec_path)}")
        os.makedirs(os.path.dirname(spec_path), exist_ok=True)
        logger.info(f"Downloading OpenAPI spec from {download_url}")
        try:
            resp = requests.get(download_url)
            logger.info(f"Download response status: {resp.status_code}")
            resp.raise_for_status()
            with open(spec_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"OpenAPI spec successfully downloaded to {spec_path}, size: {len(resp.content)} bytes")
        except requests.RequestException as e:
            logger.error(f"Failed to download OpenAPI spec: {str(e)}")
            logger.error(traceback.format_exc())
            sys.exit(1)
    else:
        # use your checked‑in YAML in src/
        spec_path = local_spec
        logger.info(f"Using local OpenAPI spec at {spec_path}")
        if not os.path.exists(spec_path):
            logger.error(f"Local OpenAPI spec not found at {spec_path}")
            sys.exit(1)

    # now load it
    logger.info(f"Attempting to load OpenAPI spec from {spec_path}")
    try:
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
            logger.info(f"Successfully loaded OpenAPI spec with version {spec.get('info', {}).get('version', 'unknown')}")
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load OpenAPI spec: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Check if servers exists in the spec
    if not spec.get('servers', []):
        logger.error("No servers found in OpenAPI spec")
        sys.exit(1)
        
    base_url = spec["servers"][0]["url"]
    logger.info(f"Using base URL: {base_url}")

    def _create_salable_tool(path, method, operation):
        logger.info(f"Creating tool for {method.upper()} {path}")
        name = f"{TOOL_PREFIX}_{method}_{path}".lower().replace('/', '_').replace('{', '').replace('}', '').replace('-', '_')
        logger.debug(f"Tool name will be: {name}")
        parameters = operation.get('parameters', [])
        responses = operation.get('responses', {})

        def _tool(**kwargs):
            token = os.getenv('SALABLE_API_TOKEN')
            if not token:
                logger.warning("SALABLE_API_TOKEN environment variable is not set")
                
            request_id = str(uuid.uuid4())
            headers = {
                'x-api-key': token,
                'version': spec['info']['version'],
                'unique-key': request_id,
                'Accept': 'application/json'
            }
            logger.debug(f"Request headers: {headers}")
            
            # build URL and query params
            try:
                url = base_url + path.format(**kwargs)
                logger.info(f"Formatted URL: {url}")
            except KeyError as e:
                logger.error(f"Missing path parameter: {str(e)}")
                logger.error(f"Available kwargs: {kwargs}")
                raise
                
            query = {p['name']: kwargs.get(p['name']) for p in parameters if p.get('in') == 'query'}
            body = kwargs.get('body', None)
            
            logger.info(f"API Call: {method.upper()} {url} (Request ID: {request_id})")
            if query:
                logger.info(f"Query params: {query}")
            if body:
                logger.info(f"Request body: {body}")
                
            try:
                resp = requests.request(
                    method.upper(), 
                    url, 
                    headers=headers, 
                    params={k:v for k,v in query.items() if v is not None}, 
                    json=body
                )
                logger.info(f"API Response: Status {resp.status_code} for {method.upper()} {url} (Request ID: {request_id})")
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                logger.error(f"API request failed: {str(e)}")
                logger.error(traceback.format_exc())
                raise

        # attach standard metadata
        _tool.__name__        = name
        _tool.__doc__         = operation.get('description', '')
        _tool._openapi_path   = path
        _tool._openapi_method = method
        _tool._parameters     = parameters
        _tool._responses      = responses
        _tool._tags           = operation.get('tags', [])

        # now register
        logger.info(f"Registering tool: {name} for {method.upper()} {path}")
        mcp.tool()(_tool)
        return name

    logger.info(f"Starting to register tools with prefix: {TOOL_PREFIX}")
    tool_count = 0
    for path, methods in spec['paths'].items():
        for method, operation in methods.items():
            tool_name = _create_salable_tool(path, method, operation)
            tool_count += 1
    logger.info(f"Registered {tool_count} tools from the OpenAPI specification")

except Exception as e:
    logger.error(f"Initialization failed: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)

if __name__ == "__main__":
    if os.getenv("RUNNING_IN_PRODUCTION"):
        # Production mode with multiple workers for better performance
        logger.info(f"Starting server in production mode with {(multiprocessing.cpu_count() * 2) + 1} workers")
        uvicorn.run(
            "server:app",  # Pass as import string
            host="0.0.0.0",
            port=3000,
            workers=(multiprocessing.cpu_count() * 2) + 1,
            timeout_keep_alive=300,  # Increased for SSE connections
            log_level="info"
        )
    else:
        # Development mode with a single worker for easier debugging
        logger.info("Starting server in development mode")
        uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True, log_level="info")