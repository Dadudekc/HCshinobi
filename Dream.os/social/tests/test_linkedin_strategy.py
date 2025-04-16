import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import requests
import pytest
from unittest import mock
from selenium.common.exceptions import TimeoutException

# Add project root to sys.path
script_dir = os.path.dirname(__file__) # tests/
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels to D:/Dream.os/
# Add social directory first if needed for strategy import
social_dir = os.path.join(project_root, 'social')
if os.path.isdir(social_dir) and social_dir not in sys.path:
     sys.path.insert(0, social_dir)
if project_root not in sys.path:
     sys.path.insert(0, project_root)

# Updated import paths
# from strategies.linkedin_strategy import LinkedInStrategy
from core.strategies.linkedin_strategy import LinkedInStrategy
# from strategies.base_strategy import BaseSocialStrategy
from core.strategies.base_strategy import BaseSocialStrategy
# from strategy_exceptions import LoginError, PostError
from core.exceptions.strategy_exceptions import LoginError, PostError

# Mock setup_logging
@pytest.fixture(autouse=True)
def mock_setup_logging():
    pass

@unittest.skipIf(LinkedInStrategy is None, "LinkedInStrategy could not be imported.")
class TestLinkedInStrategy(unittest.TestCase):

    def setUp(self):
        """Set up common resources for LinkedIn tests."""
        # Mock configuration data needed by the strategy
        self.mock_config = {
            "linkedin": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uri": "https://example.com/callback",
                "access_token": None, # Start without a token initially
                "refresh_token": None,
                "token_expiry": None
                # Add other config keys if the strategy uses them
            },
            "common_settings": {
                "timeout_seconds": 10
            }
        }
        # Mock driver (set to None, as LinkedIn uses API not Selenium)
        self.mock_driver = None
        
        # Instantiate the strategy with mocks
        self.strategy = LinkedInStrategy(self.mock_config, self.mock_driver)
        
        # Keep track of patched objects if needed across tests
        self.patches = {}
        self.mock_requests = None

    def start_patch(self, target, **kwargs):
        """Helper to start a patch and store it for stopping later."""
        patcher = patch(target, **kwargs)
        self.patches[target] = patcher
        return patcher.start()

    def tearDown(self):
        """Stop all patches started during the test."""
        for patcher in self.patches.values():
            patcher.stop()
        self.patches = {}

    # --- OAuth Flow Tests ---
    
    @patch('requests.post') # Patch the specific function used for token exchange
    @patch('strategies.linkedin_strategy.LinkedInStrategy._make_api_request') # Patch the helper used for /me
    def test_login_success(self, mock_make_api_request, mock_requests_post):
        """Test successful OAuth token exchange and author URN fetching."""
        # Mock token exchange response
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_access_token_123",
            "expires_in": 3600
        }
        mock_requests_post.return_value = mock_token_response
        
        # Mock /me response (using the mocked helper method)
        mock_me_response = MagicMock()
        mock_me_response.status_code = 200
        mock_me_response.json.return_value = {"id": "urn:li:person:testuser"}
        mock_make_api_request.return_value = mock_me_response

        # Add the required authorization_code to the config for this test
        self.strategy.config['linkedin']['authorization_code'] = "test_auth_code"
        
        # Call the login method
        result = self.strategy.login()
        
        self.assertTrue(result) # Login should succeed
        self.assertTrue(self.strategy.logged_in)
        self.assertEqual(self.strategy.access_token, "test_access_token_123")
        self.assertEqual(self.strategy.author_urn, "urn:li:person:testuser")
        
        # Verify requests.post was called correctly for token
        mock_requests_post.assert_called_once()
        call_args, call_kwargs = mock_requests_post.call_args
        self.assertEqual(call_args[0], self.strategy.TOKEN_URL)
        self.assertEqual(call_kwargs['data']['grant_type'], 'authorization_code')
        self.assertEqual(call_kwargs['data']['code'], 'test_auth_code')
        self.assertEqual(call_kwargs['data']['client_id'], 'test_client_id')
        
        # Verify _make_api_request was called for /me
        mock_make_api_request.assert_called_once_with("GET", self.strategy.ME_URL)

    @patch('requests.post')
    def test_login_token_exchange_fails(self, mock_requests_post):
        """Test login failure when the token exchange API call fails."""
        # Mock token exchange failure (e.g., 400 Bad Request)
        mock_token_response = MagicMock()
        mock_token_response.status_code = 400
        mock_token_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_token_response)
        mock_token_response.text = '{"error": "invalid_grant"}'
        mock_requests_post.return_value = mock_token_response
        
        self.strategy.config['linkedin']['authorization_code'] = "test_auth_code"
        
        result = self.strategy.login()
        
        self.assertFalse(result)
        self.assertFalse(self.strategy.logged_in)
        self.assertIsNone(self.strategy.access_token)
        mock_requests_post.assert_called_once() # Ensure the attempt was made
        # Optionally, verify logging of the HTTPError

    # @patch('requests.post')
    # def test_get_access_token_failure(self, mock_post):
    #     # Mock requests.post response for failed token exchange (e.g., 400 error)
    #     # Call strategy._get_access_token(auth_code)
    #     # Assert requests.post was called
    #     # Assert token fields are NOT updated
    #     # Assert False is returned or exception raised
    #     pass
        
    # @patch('requests.post')
    # def test_refresh_access_token_success(self, mock_post):
    #     # Set up initial expired/valid refresh token in config
    #     # Mock requests.post response for successful refresh
    #     # Call strategy._refresh_access_token()
    #     # Assert requests.post called correctly with refresh token
    #     # Assert new access_token and expiry are stored
    #     pass
        
    # --- Posting Flow Tests ---
    
    @patch('strategies.linkedin_strategy.LinkedInStrategy._make_api_request')
    def test_post_text_success(self, mock_make_api_request):
        """Test posting text successfully."""
        # Simulate logged-in state
        self.strategy.logged_in = True
        self.strategy.access_token = "test_token"
        self.strategy.author_urn = "urn:li:person:testuser"
        
        # Mock the response for the UGC post API call
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201 # Created
        mock_post_response.headers = {'x-restli-id': 'test_post_urn_123'}
        mock_make_api_request.return_value = mock_post_response
        
        post_text = "This is a test post via the API."
        result = self.strategy.post(text=post_text)
        
        self.assertTrue(result)
        # Verify _make_api_request was called correctly
        mock_make_api_request.assert_called_once()
        call_args, call_kwargs = mock_make_api_request.call_args
        self.assertEqual(call_args[0], "POST") # Method
        self.assertEqual(call_args[1], self.strategy.UGC_POSTS_URL) # URL
        
        # Check the JSON payload structure
        payload = call_kwargs['json_data']
        self.assertEqual(payload['author'], self.strategy.author_urn)
        self.assertEqual(payload['lifecycleState'], "PUBLISHED")
        content = payload['specificContent']['com.linkedin.ugc.ShareContent']
        self.assertEqual(content['shareCommentary']['text'], post_text)
        self.assertEqual(content['shareMediaCategory'], "NONE") # Text post
        self.assertIn("com.linkedin.ugc.MemberNetworkVisibility", payload['visibility'])
        # Optionally verify logging

    def test_post_requires_login(self):
        """Test that posting fails if the agent is not logged in."""
        # Ensure logged_in is False (default from setUp)
        self.strategy.logged_in = False
        self.strategy.access_token = None
        self.strategy.author_urn = None

        # Patch the API call method to ensure it's not called
        with patch('strategies.linkedin_strategy.LinkedInStrategy._make_api_request') as mock_make_api_request:
            result = self.strategy.post(text="Should not be posted")
            self.assertFalse(result)
            mock_make_api_request.assert_not_called()

    @patch('strategies.linkedin_strategy.LinkedInStrategy._make_api_request')
    def test_post_handles_api_error(self, mock_make_api_request):
        """Test handling of HTTP errors during the post API call."""
        # Simulate logged-in state
        self.strategy.logged_in = True
        self.strategy.access_token = "test_token"
        self.strategy.author_urn = "urn:li:person:testuser"
        
        # Mock the API call to raise an HTTPError
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = '{"error": "forbidden"}'
        http_error = requests.exceptions.HTTPError(response=mock_response)
        # Have the helper raise the error when called
        mock_make_api_request.side_effect = http_error
        
        result = self.strategy.post(text="This post will cause an error")
        
        self.assertFalse(result)
        mock_make_api_request.assert_called_once() # Ensure the call was attempted
        # Optionally verify logging

    # @patch('requests.post')
    # def test_post_requires_login_or_token(self, mock_post):
    #     # Ensure no access token in config
    #     # Call strategy.post(text="Test Post")
    #     # Assert post fails (returns False or raises)
    #     # Assert requests.post was NOT called
    #     pass

    # --- Add tests for image posting if implemented ---
    
    @patch('strategies.linkedin_strategy.LinkedInStrategy._make_api_request')
    def test_register_image_upload_success(self, mock_make_api_request):
        """Test successful image upload registration."""
        # Simulate logged-in state with author URN
        self.strategy.access_token = "test_token"
        self.strategy.author_urn = "urn:li:person:testuser"
        
        # Mock the API response for registration
        mock_register_response = MagicMock()
        mock_register_response.status_code = 200
        mock_register_response.json.return_value = {
            "value": {
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://upload.linkedin.com/media/upload/C5600AQF1...?upid=...&token=..."
                    }
                },
                "asset": "urn:li:digitalmediaAsset:C56...",
                "mediaArtifact": "urn:li:digitalmediaMediaArtifact:(urn:li:digitalmediaAsset:C56..,feedshare-image)"
            }
        }
        mock_make_api_request.return_value = mock_register_response
        
        asset_urn, upload_url = self.strategy._register_image_upload()
        
        self.assertEqual(asset_urn, "urn:li:digitalmediaAsset:C56...")
        self.assertTrue(upload_url.startswith("https://upload.linkedin.com/media/upload/"))
        
        # Verify API call
        mock_make_api_request.assert_called_once()
        call_args, call_kwargs = mock_make_api_request.call_args
        self.assertEqual(call_args[0], "POST")
        self.assertTrue(call_args[1].startswith(self.strategy.ASSETS_URL)) # Check base URL
        self.assertIn("registerUploadRequest", call_kwargs['json_data'])
        self.assertEqual(call_kwargs['json_data']['registerUploadRequest']['owner'], self.strategy.author_urn)

    @patch('requests.put') # Patch the specific method used for binary upload
    def test_upload_image_binary_success(self, mock_requests_put):
        """Test successful upload of image binary data."""
        # Simulate valid access token
        self.strategy.access_token = "test_token"
        
        # Mock the PUT request response
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 201 # Or 200 depending on API
        mock_upload_response.raise_for_status.return_value = None # No error
        mock_requests_put.return_value = mock_upload_response
        
        # Create a dummy image file for testing
        dummy_image_path = "test_dummy_image.png"
        with open(dummy_image_path, "wb") as f:
            f.write(b"dummyimagedata") # Write some bytes
            
        upload_url = "https://upload.linkedin.com/dummy/upload/target"
        success = self.strategy._upload_image_binary(upload_url, dummy_image_path)
        
        self.assertTrue(success)
        mock_requests_put.assert_called_once()
        call_args, call_kwargs = mock_requests_put.call_args
        self.assertEqual(call_args[0], upload_url)
        self.assertIn("Authorization", call_kwargs['headers'])
        self.assertEqual(call_kwargs['headers']['Authorization'], "Bearer test_token")
        self.assertEqual(call_kwargs['data'], b"dummyimagedata")

        # Clean up dummy file
        os.remove(dummy_image_path)

    @patch('strategies.linkedin_strategy.LinkedInStrategy._register_image_upload')
    @patch('strategies.linkedin_strategy.LinkedInStrategy._upload_image_binary')
    @patch('strategies.linkedin_strategy.LinkedInStrategy._make_api_request')
    def test_post_with_image_success(self, mock_make_api_request, mock_upload_binary, mock_register_upload):
        """Test a full post including successful image registration and upload."""
        # Simulate logged-in state
        self.strategy.logged_in = True
        self.strategy.access_token = "test_token"
        self.strategy.author_urn = "urn:li:person:testuser"
        
        # Mock image handling steps
        test_asset_urn = "urn:li:digitalmediaAsset:TESTIMG123"
        mock_register_upload.return_value = (test_asset_urn, "https://upload.url")
        mock_upload_binary.return_value = True

        # Mock the final UGC post call
        mock_final_post_response = MagicMock()
        mock_final_post_response.status_code = 201
        mock_final_post_response.headers = {'x-restli-id': 'test_img_post_urn_456'}
        mock_make_api_request.return_value = mock_final_post_response

        image_path = "dummy_image_for_post.jpg"
        post_text = "Check out this image!"
        result = self.strategy.post(text=post_text, image_path=image_path)

        self.assertTrue(result)
        mock_register_upload.assert_called_once()
        mock_upload_binary.assert_called_once_with("https://upload.url", image_path)
        # Verify the final API call to UGC Posts
        mock_make_api_request.assert_called_once()
        call_args, call_kwargs = mock_make_api_request.call_args
        self.assertEqual(call_args[0], "POST")
        self.assertEqual(call_args[1], self.strategy.UGC_POSTS_URL)
        payload = call_kwargs['json_data']
        content = payload['specificContent']['com.linkedin.ugc.ShareContent']
        self.assertEqual(content['shareCommentary']['text'], post_text)
        self.assertEqual(content['shareMediaCategory'], "IMAGE")
        self.assertEqual(content['media'][0]['media'], test_asset_urn)

if __name__ == '__main__':
    unittest.main() 