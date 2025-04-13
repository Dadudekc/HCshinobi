from typing import Dict, List, Optional, Any, Callable
import logging
from datetime import datetime, timedelta
import json
import asyncio
from dataclasses import dataclass
from collections import defaultdict
import jwt
from aiohttp import web
import aiohttp
from ratelimit import limits, RateLimitException

@dataclass
class Route:
    """Represents an API route configuration."""
    path: str
    service: str
    methods: List[str]
    auth_required: bool = True
    rate_limit: Optional[int] = None  # requests per minute
    transform_request: Optional[Callable] = None
    transform_response: Optional[Callable] = None

class APIGateway:
    """API Gateway for managing service requests, authentication, and rate limiting."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the API Gateway.
        
        Args:
            config: Gateway configuration including routes, auth settings, and rate limits
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.routes: Dict[str, Route] = {}
        self.service_registry: Dict[str, str] = {}  # service name to URL mapping
        self.rate_limiters: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        self.app = web.Application()
        self._setup_routes()
        
    def _setup_routes(self) -> None:
        """Set up API routes from configuration."""
        for route_config in self.config.get("routes", []):
            route = Route(
                path=route_config["path"],
                service=route_config["service"],
                methods=route_config.get("methods", ["GET"]),
                auth_required=route_config.get("auth_required", True),
                rate_limit=route_config.get("rate_limit"),
                transform_request=route_config.get("transform_request"),
                transform_response=route_config.get("transform_response")
            )
            self.routes[route.path] = route
            
            # Register route handlers
            for method in route.methods:
                self.app.router.add_route(
                    method,
                    route.path,
                    self._handle_request
                )
                
    async def _verify_auth(self, request: web.Request) -> bool:
        """Verify authentication token.
        
        Args:
            request: Incoming request
            
        Returns:
            True if authentication is valid, False otherwise
        """
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return False
                
            token = auth_header.split(" ")[1]
            jwt.decode(
                token,
                self.config["auth"]["secret_key"],
                algorithms=["HS256"]
            )
            return True
            
        except jwt.InvalidTokenError:
            return False
            
    def _check_rate_limit(self, client_id: str, route: Route) -> bool:
        """Check if request is within rate limits.
        
        Args:
            client_id: Client identifier
            route: Route being accessed
            
        Returns:
            True if within limits, False otherwise
        """
        if not route.rate_limit:
            return True
            
        now = datetime.now()
        client_requests = self.rate_limiters[route.path]
        
        # Clean up old entries
        client_requests = {
            k: v for k, v in client_requests.items()
            if now - v < timedelta(minutes=1)
        }
        
        # Check limit
        if len(client_requests) >= route.rate_limit:
            return False
            
        # Record request
        client_requests[client_id] = now
        self.rate_limiters[route.path] = client_requests
        return True
        
    async def _transform_request(self, request: web.Request, route: Route) -> Dict:
        """Transform incoming request based on route configuration.
        
        Args:
            request: Incoming request
            route: Route configuration
            
        Returns:
            Transformed request data
        """
        try:
            if request.content_type == "application/json":
                data = await request.json()
            else:
                data = await request.post()
                
            if route.transform_request:
                return route.transform_request(data)
            return dict(data)
            
        except Exception as e:
            self.logger.error(f"Request transformation failed: {str(e)}")
            raise web.HTTPBadRequest(text=str(e))
            
    def _transform_response(self, response: Dict, route: Route) -> Dict:
        """Transform outgoing response based on route configuration.
        
        Args:
            response: Response data
            route: Route configuration
            
        Returns:
            Transformed response data
        """
        try:
            if route.transform_response:
                return route.transform_response(response)
            return response
            
        except Exception as e:
            self.logger.error(f"Response transformation failed: {str(e)}")
            raise web.HTTPInternalServerError(text=str(e))
            
    async def _forward_request(self, request: web.Request, route: Route, data: Dict) -> web.Response:
        """Forward request to appropriate service.
        
        Args:
            request: Original request
            route: Route configuration
            data: Transformed request data
            
        Returns:
            Service response
        """
        service_url = self.service_registry.get(route.service)
        if not service_url:
            raise web.HTTPServiceUnavailable(
                text=f"Service {route.service} not available"
            )
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    request.method,
                    f"{service_url}{request.path}",
                    json=data,
                    headers=request.headers
                ) as response:
                    response_data = await response.json()
                    return web.json_response(
                        self._transform_response(response_data, route)
                    )
                    
        except Exception as e:
            self.logger.error(f"Request forwarding failed: {str(e)}")
            raise web.HTTPBadGateway(text=str(e))
            
    async def _handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming API request.
        
        Args:
            request: Incoming request
            
        Returns:
            API response
        """
        route = self.routes.get(request.path)
        if not route:
            raise web.HTTPNotFound()
            
        # Check authentication
        if route.auth_required and not await self._verify_auth(request):
            raise web.HTTPUnauthorized()
            
        # Check rate limit
        client_id = request.headers.get("X-Client-ID", request.remote)
        if not self._check_rate_limit(client_id, route):
            raise web.HTTPTooManyRequests()
            
        # Transform and forward request
        data = await self._transform_request(request, route)
        return await self._forward_request(request, route, data)
        
    def register_service(self, name: str, url: str) -> None:
        """Register a service with the gateway.
        
        Args:
            name: Service name
            url: Service URL
        """
        self.service_registry[name] = url
        self.logger.info(f"Registered service {name} at {url}")
        
    def unregister_service(self, name: str) -> None:
        """Unregister a service from the gateway.
        
        Args:
            name: Service name
        """
        if name in self.service_registry:
            del self.service_registry[name]
            self.logger.info(f"Unregistered service {name}")
            
    async def start(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Start the API Gateway server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        self.logger.info(f"API Gateway running on http://{host}:{port}")
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get gateway metrics.
        
        Returns:
            Dict containing gateway metrics
        """
        return {
            "routes": len(self.routes),
            "services": len(self.service_registry),
            "rate_limits": {
                path: len(requests)
                for path, requests in self.rate_limiters.items()
            }
        }
        
    def get_route_config(self, path: str) -> Optional[Dict]:
        """Get configuration for a specific route.
        
        Args:
            path: Route path
            
        Returns:
            Route configuration if exists, None otherwise
        """
        route = self.routes.get(path)
        if not route:
            return None
            
        return {
            "path": route.path,
            "service": route.service,
            "methods": route.methods,
            "auth_required": route.auth_required,
            "rate_limit": route.rate_limit
        }
        
    def update_rate_limit(self, path: str, limit: Optional[int]) -> bool:
        """Update rate limit for a route.
        
        Args:
            path: Route path
            limit: New rate limit (requests per minute), None to remove limit
            
        Returns:
            True if updated, False if route not found
        """
        route = self.routes.get(path)
        if not route:
            return False
            
        route.rate_limit = limit
        if limit is None and path in self.rate_limiters:
            del self.rate_limiters[path]
            
        return True 