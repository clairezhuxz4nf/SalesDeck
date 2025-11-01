import requests
import sys
import json
from datetime import datetime

class SalesDeckAPITester:
    def __init__(self, base_url="https://salesdeck-creator.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = "test_session_1762038988870"  # From auth setup
        self.user_id = "test-user-1762038988870"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'clients': [],
            'assets': [],
            'leads': [],
            'decks': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Use cookies for authentication (backend expects cookies)
        cookies = {}
        if self.session_token:
            cookies['session_token'] = self.session_token
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION ENDPOINTS")
        print("="*50)
        
        # Test /auth/me
        success, user_data = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        
        if success:
            print(f"   User: {user_data.get('name')} ({user_data.get('email')})")
        
        return success

    def test_client_endpoints(self):
        """Test client CRUD operations"""
        print("\n" + "="*50)
        print("TESTING CLIENT ENDPOINTS")
        print("="*50)
        
        # Test create client
        client_data = {
            "name": "Test Corp",
            "industry": "Technology",
            "description": "A test technology company for API testing"
        }
        
        success, client = self.run_test(
            "Create Client",
            "POST",
            "clients",
            200,
            data=client_data
        )
        
        if success and client.get('id'):
            self.created_resources['clients'].append(client['id'])
            print(f"   Created client ID: {client['id']}")
        
        # Test get clients
        success, clients = self.run_test(
            "Get Clients",
            "GET",
            "clients",
            200
        )
        
        if success:
            print(f"   Found {len(clients)} clients")
        
        return len(self.created_resources['clients']) > 0

    def test_asset_endpoints(self):
        """Test asset CRUD operations"""
        print("\n" + "="*50)
        print("TESTING ASSET ENDPOINTS")
        print("="*50)
        
        # Test create product description asset
        asset_data = {
            "type": "product_description",
            "name": "AI Sales Platform",
            "content": "Our AI-powered sales platform helps B2B SaaS companies generate personalized sales presentations in minutes, saving 10-15 hours per week and accelerating sales cycles by 40%."
        }
        
        success, asset = self.run_test(
            "Create Product Description Asset",
            "POST",
            "assets",
            200,
            data=asset_data
        )
        
        if success and asset.get('id'):
            self.created_resources['assets'].append(asset['id'])
            print(f"   Created asset ID: {asset['id']}")
        
        # Test create use case asset
        use_case_data = {
            "type": "use_case",
            "name": "Healthcare Industry Use Case",
            "content": "Healthcare organizations use our platform to create HIPAA-compliant sales presentations for medical device sales, reducing preparation time by 75% while ensuring regulatory compliance."
        }
        
        success, asset = self.run_test(
            "Create Use Case Asset",
            "POST",
            "assets",
            200,
            data=use_case_data
        )
        
        if success and asset.get('id'):
            self.created_resources['assets'].append(asset['id'])
        
        # Test get assets
        success, assets = self.run_test(
            "Get All Assets",
            "GET",
            "assets",
            200
        )
        
        if success:
            print(f"   Found {len(assets)} assets")
        
        # Test get assets by type
        success, product_assets = self.run_test(
            "Get Product Description Assets",
            "GET",
            "assets?asset_type=product_description",
            200
        )
        
        if success:
            print(f"   Found {len(product_assets)} product description assets")
        
        return len(self.created_resources['assets']) > 0

    def test_lead_endpoints(self):
        """Test lead CRUD operations"""
        print("\n" + "="*50)
        print("TESTING LEAD ENDPOINTS")
        print("="*50)
        
        if not self.created_resources['clients']:
            print("❌ No clients available for lead creation")
            return False
        
        # Test create lead
        lead_data = {
            "client_id": self.created_resources['clients'][0],
            "project_scope": "Implement AI-powered sales deck generation system for their B2B SaaS sales team. Need to integrate with existing CRM and support 50+ sales reps.",
            "notes": "High priority client. Decision maker is VP of Sales. Budget approved for Q1. Looking for 3-month implementation timeline."
        }
        
        success, lead = self.run_test(
            "Create Lead",
            "POST",
            "leads",
            200,
            data=lead_data
        )
        
        if success and lead.get('id'):
            self.created_resources['leads'].append(lead['id'])
            print(f"   Created lead ID: {lead['id']}")
            print(f"   Client: {lead.get('client_name')}")
        
        # Test get leads
        success, leads = self.run_test(
            "Get Leads",
            "GET",
            "leads",
            200
        )
        
        if success:
            print(f"   Found {len(leads)} leads")
        
        # Test update lead status
        if self.created_resources['leads']:
            success, _ = self.run_test(
                "Update Lead Status",
                "PATCH",
                f"leads/{self.created_resources['leads'][0]}?status=won",
                200
            )
        
        return len(self.created_resources['leads']) > 0

    def test_deck_generation(self):
        """Test AI deck generation"""
        print("\n" + "="*50)
        print("TESTING DECK GENERATION")
        print("="*50)
        
        if not self.created_resources['leads']:
            print("❌ No leads available for deck generation")
            return False
        
        # Test generate deck
        deck_data = {
            "lead_id": self.created_resources['leads'][0]
        }
        
        print("   🤖 Generating AI sales deck (this may take 10-30 seconds)...")
        success, deck = self.run_test(
            "Generate Sales Deck",
            "POST",
            "decks/generate",
            200,
            data=deck_data
        )
        
        if success and deck.get('id'):
            self.created_resources['decks'].append(deck['id'])
            print(f"   Created deck ID: {deck['id']}")
            print(f"   Deck title: {deck.get('content', {}).get('title', 'N/A')}")
            slides = deck.get('content', {}).get('slides', [])
            print(f"   Number of slides: {len(slides)}")
            
            # Print slide types
            if slides:
                slide_types = [slide.get('type', 'unknown') for slide in slides]
                print(f"   Slide types: {', '.join(slide_types)}")
        
        # Test get decks
        success, decks = self.run_test(
            "Get All Decks",
            "GET",
            "decks",
            200
        )
        
        if success:
            print(f"   Found {len(decks)} decks")
        
        # Test get specific deck
        if self.created_resources['decks']:
            success, deck_detail = self.run_test(
                "Get Specific Deck",
                "GET",
                f"decks/{self.created_resources['decks'][0]}",
                200
            )
            
            if success:
                print(f"   Retrieved deck: {deck_detail.get('content', {}).get('title', 'N/A')}")
        
        return len(self.created_resources['decks']) > 0

    def test_logout(self):
        """Test logout functionality"""
        print("\n" + "="*50)
        print("TESTING LOGOUT")
        print("="*50)
        
        success, _ = self.run_test(
            "Logout",
            "POST",
            "auth/logout",
            200
        )
        
        return success

    def cleanup_resources(self):
        """Clean up created test resources"""
        print("\n" + "="*50)
        print("CLEANING UP TEST RESOURCES")
        print("="*50)
        
        # Delete leads
        for lead_id in self.created_resources['leads']:
            self.run_test(f"Delete Lead {lead_id}", "DELETE", f"leads/{lead_id}", 200)
        
        # Delete assets
        for asset_id in self.created_resources['assets']:
            self.run_test(f"Delete Asset {asset_id}", "DELETE", f"assets/{asset_id}", 200)
        
        # Delete clients
        for client_id in self.created_resources['clients']:
            self.run_test(f"Delete Client {client_id}", "DELETE", f"clients/{client_id}", 200)

def main():
    print("🚀 Starting Sales Deck API Testing")
    print(f"Backend URL: https://salesdeck-creator.preview.emergentagent.com")
    
    tester = SalesDeckAPITester()
    
    # Run all tests
    auth_success = tester.test_auth_endpoints()
    if not auth_success:
        print("\n❌ Authentication failed - stopping tests")
        return 1
    
    client_success = tester.test_client_endpoints()
    asset_success = tester.test_asset_endpoints()
    lead_success = tester.test_lead_endpoints()
    deck_success = tester.test_deck_generation()
    logout_success = tester.test_logout()
    
    # Cleanup
    tester.cleanup_resources()
    
    # Print final results
    print("\n" + "="*60)
    print("FINAL TEST RESULTS")
    print("="*60)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"🔐 Authentication: {'✅' if auth_success else '❌'}")
    print(f"👥 Clients CRUD: {'✅' if client_success else '❌'}")
    print(f"📄 Assets CRUD: {'✅' if asset_success else '❌'}")
    print(f"🎯 Leads CRUD: {'✅' if lead_success else '❌'}")
    print(f"🤖 AI Deck Generation: {'✅' if deck_success else '❌'}")
    print(f"🚪 Logout: {'✅' if logout_success else '❌'}")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
    
    return 0 if success_rate >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())