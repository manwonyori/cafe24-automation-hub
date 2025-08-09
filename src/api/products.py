"""
Product API for Cafe24
Handles all product-related operations
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .client import Cafe24Client
from ..core.exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)

class ProductAPI:
    """Product management API"""
    
    def __init__(self, client: Optional[Cafe24Client] = None):
        """
        Initialize Product API
        
        Args:
            client: Optional pre-configured Cafe24Client
        """
        self.client = client or Cafe24Client()
    
    async def get_products(self, 
                          limit: int = 100, 
                          offset: int = 0,
                          fields: Optional[List[str]] = None,
                          **filters) -> Dict[str, Any]:
        """
        Get list of products
        
        Args:
            limit: Maximum number of products to return (max 500)
            offset: Starting position
            fields: Specific fields to include
            **filters: Additional filter parameters
        
        Returns:
            Products data with pagination info
        """
        params = {
            'limit': min(limit, 500),  # API limit
            'offset': offset
        }
        
        # Add field selection
        if fields:
            params['fields'] = ','.join(fields)
        
        # Add filters
        params.update(filters)
        
        try:
            response = await self.client.get('products', params=params)
            
            # Normalize response format
            products = response.get('products', [])
            
            return {
                'products': products,
                'total_count': len(products),
                'limit': limit,
                'offset': offset,
                'has_more': len(products) == limit
            }
            
        except Exception as e:
            logger.error(f"Failed to get products: {e}")
            raise APIError(f"Failed to retrieve products: {str(e)}")
    
    async def get_product(self, product_no: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get single product by product number
        
        Args:
            product_no: Product number
            
        Returns:
            Product data or None if not found
        """
        try:
            response = await self.client.get(f'products/{product_no}')
            
            # Handle different response formats
            if 'product' in response:
                return response['product']
            elif 'products' in response and response['products']:
                return response['products'][0]
            else:
                return response
                
        except APIError as e:
            if e.status_code == 404:
                logger.warning(f"Product not found: {product_no}")
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get product {product_no}: {e}")
            raise APIError(f"Failed to retrieve product: {str(e)}")
    
    async def search_products(self, 
                            query: str,
                            search_type: str = 'product_name',
                            limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search products by various criteria
        
        Args:
            query: Search query
            search_type: Type of search (product_name, product_code, etc.)
            limit: Maximum results
            
        Returns:
            List of matching products
        """
        # Map search types to API parameters
        search_params = {}
        
        if search_type == 'product_name':
            search_params['product_name'] = query
        elif search_type == 'product_code':
            search_params['product_code'] = query
        elif search_type == 'brand_name':
            search_params['brand_name'] = query
        else:
            # Generic search
            search_params['product_name'] = query
        
        try:
            result = await self.get_products(limit=limit, **search_params)
            return result.get('products', [])
            
        except Exception as e:
            logger.error(f"Product search failed: {e}")
            raise APIError(f"Product search failed: {str(e)}")
    
    async def update_product(self, 
                           product_no: Union[str, int],
                           updates: Dict[str, Any],
                           shop_no: int = 1) -> bool:
        """
        Update product information
        
        Args:
            product_no: Product number to update
            updates: Dictionary of fields to update
            shop_no: Shop number (default: 1)
            
        Returns:
            Success status
        """
        # Validate required fields
        if not updates:
            raise ValidationError("No updates provided")
        
        # Prepare request data
        request_data = {
            'shop_no': shop_no,
            'request': updates
        }
        
        try:
            await self.client.put(f'products/{product_no}', json_data=request_data)
            logger.info(f"Successfully updated product {product_no}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update product {product_no}: {e}")
            raise APIError(f"Failed to update product: {str(e)}")
    
    async def update_product_price(self, 
                                 product_no: Union[str, int],
                                 price: Union[str, int, float],
                                 retail_price: Optional[Union[str, int, float]] = None,
                                 supply_price: Optional[Union[str, int, float]] = None,
                                 shop_no: int = 1) -> bool:
        """
        Update product price (convenience method)
        
        Args:
            product_no: Product number
            price: New selling price
            retail_price: Retail price (optional, defaults to price)
            supply_price: Supply price (optional, calculated as 70% of price)
            shop_no: Shop number
            
        Returns:
            Success status
        """
        price = str(price)
        
        updates = {
            'price': price,
            'retail_price': retail_price or price,
        }
        
        # Calculate supply price if not provided
        if supply_price is None:
            supply_price = str(int(float(price) * 0.7))
        updates['supply_price'] = str(supply_price)
        
        return await self.update_product(product_no, updates, shop_no)
    
    async def update_product_stock(self,
                                 product_no: Union[str, int],
                                 stock_quantity: int,
                                 shop_no: int = 1) -> bool:
        """
        Update product stock quantity
        
        Args:
            product_no: Product number
            stock_quantity: New stock quantity
            shop_no: Shop number
            
        Returns:
            Success status
        """
        updates = {
            'stock_quantity': str(stock_quantity)
        }
        
        return await self.update_product(product_no, updates, shop_no)
    
    async def get_all_products(self, 
                             batch_size: int = 100,
                             fields: Optional[List[str]] = None,
                             progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Get all products with pagination handling
        
        Args:
            batch_size: Number of products per API call
            fields: Specific fields to retrieve
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of all products
        """
        all_products = []
        offset = 0
        total_fetched = 0
        
        logger.info("Starting to fetch all products...")
        
        while True:
            try:
                result = await self.get_products(
                    limit=batch_size, 
                    offset=offset,
                    fields=fields
                )
                
                products = result.get('products', [])
                
                if not products:
                    break
                
                all_products.extend(products)
                total_fetched += len(products)
                
                # Progress callback
                if progress_callback:
                    progress_callback(total_fetched, len(products))
                
                logger.debug(f"Fetched {len(products)} products (total: {total_fetched})")
                
                # Check if we got fewer products than requested (end of data)
                if len(products) < batch_size:
                    break
                
                offset += batch_size
                
            except Exception as e:
                logger.error(f"Error fetching products at offset {offset}: {e}")
                break
        
        logger.info(f"Completed fetching {total_fetched} products")
        return all_products
    
    async def bulk_update_prices(self,
                               price_updates: Dict[Union[str, int], Union[str, int, float]],
                               batch_size: int = 10,
                               progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Update multiple product prices in batches
        
        Args:
            price_updates: Dict mapping product_no to new price
            batch_size: Number of updates per batch
            progress_callback: Optional progress callback
            
        Returns:
            Results summary
        """
        total_updates = len(price_updates)
        successful_updates = 0
        failed_updates = []
        
        logger.info(f"Starting bulk price update for {total_updates} products")
        
        # Process in batches
        items = list(price_updates.items())
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            for product_no, new_price in batch:
                try:
                    success = await self.update_product_price(product_no, new_price)
                    if success:
                        successful_updates += 1
                    else:
                        failed_updates.append({'product_no': product_no, 'error': 'Update returned False'})
                        
                except Exception as e:
                    failed_updates.append({'product_no': product_no, 'error': str(e)})
                    logger.error(f"Failed to update price for product {product_no}: {e}")
            
            # Progress callback
            if progress_callback:
                completed = i + len(batch)
                progress_callback(completed, total_updates)
        
        result = {
            'total_updates': total_updates,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'success_rate': successful_updates / total_updates if total_updates > 0 else 0
        }
        
        logger.info(f"Bulk price update completed: {successful_updates}/{total_updates} successful")
        return result
    
    async def get_product_variants(self, product_no: Union[str, int]) -> List[Dict[str, Any]]:
        """
        Get product variants/options
        
        Args:
            product_no: Product number
            
        Returns:
            List of product variants
        """
        try:
            response = await self.client.get(f'products/{product_no}/variants')
            return response.get('variants', [])
            
        except APIError as e:
            if e.status_code == 404:
                return []
            raise
        except Exception as e:
            logger.error(f"Failed to get variants for product {product_no}: {e}")
            raise APIError(f"Failed to retrieve product variants: {str(e)}")
    
    async def close(self):
        """Close API client"""
        await self.client.close()