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

def send_topic_notification(topic: str, title: str, body: str, data: Dict[str, str] = None, image_url: str = None) -> bool:
    """
    Broadcasts a notification with optional image to an FCM topic (e.g., 'helaGee_all_users').
    """
    _init_firebase()
    if not _initialized:
        return False
        
    try:
        data_dict = data if data else {}
        if image_url and 'image_url' not in data_dict:
            data_dict['image_url'] = image_url

        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url if image_url else None,
        )

        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                image=image_url if image_url else None,
                channel_id='com.yatra.helagee.channel.notifications',
                default_sound=True,
                default_vibrate_timings=True,
            )
        )

        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    sound='default',
                    badge=1,
                    mutable_content=True if image_url else False,
                )
            ),
            fcm_options=messaging.APNSFCMOptions(
                image=image_url if image_url else None
            ) if image_url else None
        )

        message = messaging.Message(
            notification=notification,
            android=android_config,
            apns=apns_config,
            data=data_dict,
            topic=topic,
        )
        response = messaging.send(message)
        print(f"Successfully sent message with image to topic {topic}: {response}")
        return True
    except Exception as e:
        print(f"Error sending FCM topic message: {e}")
        return False

def send_device_notification(token: str, title: str, body: str, data: Dict[str, str] = None, image_url: str = None) -> bool:
    """
    Sends a targeted notification with optional image to a specific FCM device token.
    """
    _init_firebase()
    if not _initialized:
        return False
        
    try:
        data_dict = data if data else {}
        if image_url and 'image_url' not in data_dict:
            data_dict['image_url'] = image_url

        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url if image_url else None,
        )

        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                image=image_url if image_url else None,
                channel_id='com.yatra.helagee.channel.notifications',
                default_sound=True,
            )
        )

        message = messaging.Message(
            notification=notification,
            android=android_config,
            data=data_dict,
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
