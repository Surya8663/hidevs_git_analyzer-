import logging
import time
import functools
import json
import os
from datetime import datetime

# Configure logging
log_folder = "logs"
os.makedirs(log_folder, exist_ok=True)

# Create a logger
logger = logging.getLogger('api_calls')
logger.setLevel(logging.INFO)

# Create handlers
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
file_handler = logging.FileHandler(os.path.join(log_folder, f'api_calls_{current_time}.log'))
console_handler = logging.StreamHandler()

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_api_call(func):
    """Decorator to log API calls with timing and results."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        function_name = func.__name__
        
        # Log function call
        logger.info(f"Starting {function_name}")
        logger.info(f"Arguments: {args}")
        logger.info(f"Keyword Arguments: {kwargs}")
        
        try:
            # Execute function
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log success
            logger.info(f"Completed {function_name} in {execution_time:.2f} seconds")
            logger.info(f"Result: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            # Log error
            execution_time = time.time() - start_time
            logger.error(f"Error in {function_name} after {execution_time:.2f} seconds")
            logger.error(f"Error details: {str(e)}")
            raise
            
    return wrapper