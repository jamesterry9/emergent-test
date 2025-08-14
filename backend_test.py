import requests
import sys
import time
from datetime import datetime

class ChatbotAPITester:
    def __init__(self, base_url="https://chatbot-creator-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_chatbot_id = None
        self.conversation_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {str(response_data)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_user_registration(self):
        """Test user registration"""
        test_username = f"testuser_{int(time.time())}"
        test_password = "TestPass123!"
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "api/auth/register",
            200,
            data={"username": test_username, "password": test_password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            print(f"   Registered user: {test_username}")
            return True
        return False

    def test_user_login(self):
        """Test user login with existing credentials"""
        if not self.user_data:
            print("❌ No user data available for login test")
            return False
            
        # Create a new user for login test
        test_username = f"logintest_{int(time.time())}"
        test_password = "LoginTest123!"
        
        # First register
        reg_success, reg_response = self.run_test(
            "Register for Login Test",
            "POST", 
            "api/auth/register",
            200,
            data={"username": test_username, "password": test_password}
        )
        
        if not reg_success:
            return False
            
        # Now test login
        success, response = self.run_test(
            "User Login",
            "POST",
            "api/auth/login", 
            200,
            data={"username": test_username, "password": test_password}
        )
        
        return success and 'access_token' in response

    def test_create_chatbot(self):
        """Test chatbot creation"""
        if not self.token:
            print("❌ No authentication token for chatbot creation")
            return False
            
        chatbot_data = {
            "name": "Test Bot",
            "description": "A test chatbot for API testing",
            "introduction": "Hello! I'm a test bot created for API testing purposes.",
            "is_censored": True
        }
        
        success, response = self.run_test(
            "Create Chatbot",
            "POST",
            "api/chatbots",
            200,
            data=chatbot_data
        )
        
        if success and 'id' in response:
            self.created_chatbot_id = response['id']
            print(f"   Created chatbot ID: {self.created_chatbot_id}")
            return True
        return False

    def test_get_all_chatbots(self):
        """Test getting all chatbots"""
        success, response = self.run_test(
            "Get All Chatbots",
            "GET",
            "api/chatbots",
            200
        )
        
        if success:
            print(f"   Found {len(response)} chatbots")
            return True
        return False

    def test_get_specific_chatbot(self):
        """Test getting a specific chatbot"""
        if not self.created_chatbot_id:
            print("❌ No chatbot ID available for specific chatbot test")
            return False
            
        success, response = self.run_test(
            "Get Specific Chatbot",
            "GET",
            f"api/chatbots/{self.created_chatbot_id}",
            200
        )
        
        return success and response.get('id') == self.created_chatbot_id

    def test_start_conversation(self):
        """Test starting a conversation with a chatbot"""
        if not self.created_chatbot_id or not self.token:
            print("❌ Missing chatbot ID or token for conversation test")
            return False
            
        success, response = self.run_test(
            "Start Conversation",
            "POST",
            f"api/chat/{self.created_chatbot_id}/start",
            200
        )
        
        if success and 'id' in response:
            self.conversation_id = response['id']
            print(f"   Started conversation ID: {self.conversation_id}")
            return True
        return False

    def test_send_message(self):
        """Test sending a message and getting AI response"""
        if not self.conversation_id or not self.token:
            print("❌ Missing conversation ID or token for message test")
            return False
            
        message_data = {
            "message": "Hello! This is a test message. Please respond."
        }
        
        success, response = self.run_test(
            "Send Message",
            "POST",
            f"api/chat/{self.conversation_id}/message",
            200,
            data=message_data
        )
        
        if success:
            user_msg = response.get('user_message', {})
            bot_msg = response.get('bot_response', {})
            
            if user_msg and bot_msg:
                print(f"   User message: {user_msg.get('content', '')[:50]}...")
                print(f"   Bot response: {bot_msg.get('content', '')[:50]}...")
                return True
        return False

    def test_get_conversation_messages(self):
        """Test getting conversation messages"""
        if not self.conversation_id or not self.token:
            print("❌ Missing conversation ID or token for messages test")
            return False
            
        success, response = self.run_test(
            "Get Conversation Messages",
            "GET",
            f"api/chat/{self.conversation_id}/messages",
            200
        )
        
        if success:
            print(f"   Found {len(response)} messages in conversation")
            return True
        return False

    def test_get_user_conversations(self):
        """Test getting user's conversations"""
        if not self.token:
            print("❌ No token for conversations test")
            return False
            
        success, response = self.run_test(
            "Get User Conversations",
            "GET",
            "api/conversations",
            200
        )
        
        if success:
            print(f"   Found {len(response)} conversations for user")
            return True
        return False

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("🚀 Starting Chatbot API Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 50)
        
        # Authentication tests
        if not self.test_user_registration():
            print("❌ Registration failed, stopping tests")
            return False
            
        if not self.test_user_login():
            print("❌ Login test failed")
            
        # Chatbot tests
        if not self.test_create_chatbot():
            print("❌ Chatbot creation failed, stopping chat tests")
            return False
            
        self.test_get_all_chatbots()
        self.test_get_specific_chatbot()
        
        # Chat tests
        if not self.test_start_conversation():
            print("❌ Conversation start failed, stopping message tests")
            return False
            
        # Wait a bit for AI processing
        print("⏳ Waiting for AI response processing...")
        time.sleep(3)
        
        self.test_send_message()
        self.test_get_conversation_messages()
        self.test_get_user_conversations()
        
        # Print final results
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = ChatbotAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())