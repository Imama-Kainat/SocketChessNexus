import json

class Message:
    """Class for structured message communication."""
    
    def __init__(self, msg_type, data, client_id=None):
        """
        Initialize a message.
        
        Args:
            msg_type: Type of message (string)
            data: Message data (dict)
            client_id: Client ID (string, optional)
        """
        self.msg_type = msg_type
        self.data = data
        self.client_id = client_id

    def to_json(self):
        """Convert message to JSON string."""
        message_dict = {
            "msg_type": self.msg_type,
            "data": self.data
        }
        if self.client_id:
            message_dict["client_id"] = self.client_id
        return json.dumps(message_dict)

    def to_dict(self):
        """Convert message to dictionary."""
        message_dict = {
            "msg_type": self.msg_type,
            "data": self.data
        }
        if self.client_id:
            message_dict["client_id"] = self.client_id
        return message_dict

    @staticmethod
    def from_json(json_str):
        """Create a Message object from a JSON string."""
        try:
            message_dict = json.loads(json_str)
            return Message(
                msg_type=message_dict["msg_type"],
                data=message_dict["data"],
                client_id=message_dict.get("client_id")
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid message format: {e}")