from typing import Dict, Optional, Any
import json
import logging
import asyncio
from pathlib import Path
from .api_gateway import APIGateway

class GatewayService:
    """Service for managing API Gateway lifecycle and configuration."""
    
    def __init__(self, config_path: str = "config/gateway_config.json"):
        """Initialize the gateway service.
        
        Args:
            config_path: Path to gateway configuration file
        """
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        self.gateway: Optional[APIGateway] = None
        self._load_config()
        
    def _load_config(self) -> None:
        """Load gateway configuration from file."""
        try:
            with open(self.config_path) as f:
                self.config = json.load(f)
                
            # Set up logging
            logging.basicConfig(
                level=self.config["logging"]["level"],
                format=self.config["logging"]["format"]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            raise
            
    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
            raise
            
    async def start(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Start the API Gateway.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        try:
            self.gateway = APIGateway(self.config)
            
            # Register services
            for name, url in self.config["services"].items():
                self.gateway.register_service(name, url)
                
            # Start gateway
            await self.gateway.start(host, port)
            self.logger.info(f"Gateway service started on http://{host}:{port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start gateway: {str(e)}")
            raise
            
    def update_route(self, path: str, route_config: Dict[str, Any]) -> bool:
        """Update route configuration.
        
        Args:
            path: Route path
            route_config: New route configuration
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Update in-memory config
            for route in self.config["routes"]:
                if route["path"] == path:
                    route.update(route_config)
                    break
            else:
                self.config["routes"].append(route_config)
                
            # Save to file
            self._save_config()
            
            # Update gateway if running
            if self.gateway:
                self.gateway = APIGateway(self.config)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update route: {str(e)}")
            return False
            
    def update_service(self, name: str, url: str) -> bool:
        """Update service URL.
        
        Args:
            name: Service name
            url: New service URL
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Update config
            self.config["services"][name] = url
            self._save_config()
            
            # Update gateway if running
            if self.gateway:
                self.gateway.register_service(name, url)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update service: {str(e)}")
            return False
            
    def update_auth_config(self, auth_config: Dict[str, Any]) -> bool:
        """Update authentication configuration.
        
        Args:
            auth_config: New authentication configuration
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            self.config["auth"].update(auth_config)
            self._save_config()
            
            # Update gateway if running
            if self.gateway:
                self.gateway = APIGateway(self.config)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update auth config: {str(e)}")
            return False
            
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get gateway metrics.
        
        Returns:
            Dict containing metrics if gateway is running, None otherwise
        """
        if not self.gateway:
            return None
            
        try:
            return self.gateway.get_metrics()
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics: {str(e)}")
            return None
            
    def get_route_config(self, path: str) -> Optional[Dict[str, Any]]:
        """Get route configuration.
        
        Args:
            path: Route path
            
        Returns:
            Route configuration if exists, None otherwise
        """
        if not self.gateway:
            return None
            
        try:
            return self.gateway.get_route_config(path)
            
        except Exception as e:
            self.logger.error(f"Failed to get route config: {str(e)}")
            return None
            
    def update_rate_limit(self, path: str, limit: Optional[int]) -> bool:
        """Update rate limit for a route.
        
        Args:
            path: Route path
            limit: New rate limit (requests per minute), None to remove limit
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not self.gateway:
            return False
            
        try:
            # Update gateway
            if not self.gateway.update_rate_limit(path, limit):
                return False
                
            # Update config
            for route in self.config["routes"]:
                if route["path"] == path:
                    route["rate_limit"] = limit
                    break
                    
            self._save_config()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update rate limit: {str(e)}")
            return False 