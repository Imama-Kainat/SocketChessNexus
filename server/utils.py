import socket
import threading
import logging
from typing import Callable, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('server')

def setup_socket(host: str, port: int) -> socket.socket:
    """Set up a socket server."""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(10)
        logger.info(f"Server started on {host}:{port}")
        return server_socket
    except Exception as e:
        logger.error(f"Error setting up socket: {e}")
        raise

def receive_data(client_socket: socket.socket, buffer_size: int = 4096) -> str:
    """Receive data from a socket with a 4-byte length prefix."""
    try:
        # Read the 4-byte length prefix
        length_bytes = client_socket.recv(4)
        if not length_bytes:
            logger.debug("No length prefix received, connection likely closed")
            return ""
        if len(length_bytes) != 4:
            logger.error(f"Received incomplete length prefix: {length_bytes}")
            return ""
        length = int.from_bytes(length_bytes, byteorder='big')
        logger.debug(f"Expecting message of length: {length}")

        # Read the exact number of bytes specified by the length
        data = b""
        while len(data) < length:
            chunk = client_socket.recv(min(length - len(data), buffer_size))
            if not chunk:
                logger.error(f"Connection closed while reading message, received {len(data)} of {length} bytes")
                return ""
            data += chunk
        logger.debug(f"Received raw data: {data}")
        return data.decode('utf-8')
    except Exception as e:
        logger.error(f"Error receiving data: {e}")
        return ""

def send_data(client_socket: socket.socket, data: str) -> bool:
    """Send data to a socket with a 4-byte length prefix."""
    try:
        # Debug print of message being sent
        preview = data[:100] + "..." if len(data) > 100 else data
        print(f"SENDING DATA: {preview}")
        
        # Encode and prepare the message
        data_bytes = data.encode('utf-8')
        length = len(data_bytes)
        length_bytes = length.to_bytes(4, byteorder='big')
        
        # Send the message
        client_socket.sendall(length_bytes + data_bytes)
        print(f"SENT {length} bytes successfully")
        logger.debug(f"Sent {length} bytes of data")
        return True
    except Exception as e:
        logger.error(f"Error sending data: {e}")
        print(f"ERROR sending data: {e}")
        return False

def run_in_thread(target: Callable[..., Any], *args: Any, **kwargs: Any) -> threading.Thread:
    """Run a function in a separate thread."""
    thread = threading.Thread(target=target, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

def generate_unique_id() -> str:
    """Generate a unique ID."""
    import uuid
    return str(uuid.uuid4())