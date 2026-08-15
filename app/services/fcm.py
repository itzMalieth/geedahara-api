import os
import firebase_admin
from firebase_admin import credentials, messaging
from typing import Dict, Any

# Path to the Firebase service account key
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "credentials", "firebase-service-account.json"
)

# Initialize Firebase Admin SDK (lazy initialization)
_initialized = False

def _init_firebase():
    global _initialized
    if not _initialized:
        if os.path.exists(CREDENTIALS_PATH):
            try:
                cred = credentials.Certificate(CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                _initialized = True
            except ValueError:
                # App already initialized
                _initialized = True
        else:
            print(f"WARNING: Firebase credentials not found at {CREDENTIALS_PATH}. FCM disabled.")

def send_topic_notification(topic: str, title: str, body: str, data: Dict[str, str] = None) -> bool:
    """
    Broadcasts a notification to an FCM topic (e.g., 'helaGee_all_users').
    """
    _init_firebase()
    if not _initialized:
        return False
        
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data if data else {},
            topic=topic,
        )
        response = messaging.send(message)
        print(f"Successfully sent message to topic {topic}: {response}")
        return True
    except Exception as e:
        print(f"Error sending FCM topic message: {e}")
        return False

def send_device_notification(token: str, title: str, body: str, data: Dict[str, str] = None) -> bool:
    """
    Sends a targeted notification to a specific FCM device token.
    """
    _init_firebase()
    if not _initialized:
        return False
        
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data if data else {},
            token=token,
        )
        response = messaging.send(message)
        print(f"Successfully sent message to device: {response}")
        return True
    except messaging.UnregisteredError:
        print(f"Token unregistered: {token}")
        # In a robust system, you would delete this token from the DB here
        return False
    except Exception as e:
        print(f"Error sending FCM device message: {e}")
        return False
