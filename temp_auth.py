import requests

# The base URL of the API
BASE_URL = "http://localhost:8001"

# The user to create
USER = {
    "username": "test@example.com",
    "password": "password"
}

def register_user():
    """Registers a new user."""
    try:
        response = requests.post(f"{BASE_URL}/api/register", data=USER)
        if response.status_code == 200:
            print("User registered successfully.")
        elif response.status_code == 400 and "Email already registered" in response.text:
            print("User already registered.")
        else:
            print(f"Error registering user: {response.status_code} {response.text}")
            raise Exception("Could not register user")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        raise

def get_token():
    """Gets an access token for the user."""
    response = requests.post(f"{BASE_URL}/api/token", data=USER)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"Access token: {token}")
        return token
    else:
        print(f"Error getting token: {response.status_code} {response.text}")
        raise Exception("Could not get token")

if __name__ == "__main__":
    register_user()
    get_token()
