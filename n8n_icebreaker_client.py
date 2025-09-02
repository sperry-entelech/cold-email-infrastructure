#!/usr/bin/env python3
"""
n8n Claude Icebreaker Client
Integrates with n8n workflow for icebreaker generation using Claude
"""

import requests
import json
import logging
from typing import Dict, Optional
from dataclasses import dataclass
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Lead:
    """Lead data structure for icebreaker generation"""
    first_name: str
    last_name: str
    email: str
    company_name: str
    industry: str = ""
    website: str = ""
    title: str = ""

class N8nIcebreakerClient:
    """Client for generating icebreakers via n8n workflow"""
    
    def __init__(self, n8n_webhook_url: str = None):
        """
        Initialize the n8n client
        
        Args:
            n8n_webhook_url: Full webhook URL for the n8n workflow
                           Can also be set via N8N_ICEBREAKER_WEBHOOK_URL env var
        """
        self.webhook_url = n8n_webhook_url or os.getenv('N8N_ICEBREAKER_WEBHOOK_URL')
        
        if not self.webhook_url:
            raise ValueError("n8n webhook URL required. Set N8N_ICEBREAKER_WEBHOOK_URL environment variable or pass as parameter.")
        
        # Validate URL format
        if not self.webhook_url.startswith(('http://', 'https://')):
            raise ValueError("Invalid webhook URL format. Must start with http:// or https://")
        
        logger.info(f"n8n Icebreaker Client initialized with webhook: {self.webhook_url}")
    
    def generate_icebreaker(self, lead: Lead, template: str = None) -> Dict:
        """
        Generate icebreaker for a lead using n8n workflow
        
        Args:
            lead: Lead data
            template: Optional custom template format
            
        Returns:
            Dict with icebreaker, status, and metadata
        """
        payload = {
            'company_name': lead.company_name,
            'industry': lead.industry,
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'title': lead.title,
            'website': lead.website,
        }
        
        if template:
            payload['template'] = template
        
        try:
            logger.info(f"Generating icebreaker for {lead.company_name} via n8n workflow...")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully generated icebreaker: {result.get('icebreaker', '')[:50]}...")
                return result
            else:
                logger.error(f"n8n workflow failed: {response.status_code} - {response.text}")
                return self._get_fallback_response(lead, f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("n8n workflow timeout")
            return self._get_fallback_response(lead, "Request timeout")
            
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to n8n workflow")
            return self._get_fallback_response(lead, "Connection error")
            
        except Exception as e:
            logger.error(f"Error calling n8n workflow: {e}")
            return self._get_fallback_response(lead, str(e))
    
    def _get_fallback_response(self, lead: Lead, error: str) -> Dict:
        """Generate fallback response when n8n workflow fails"""
        fallback_template = os.getenv('ICEBREAKER_FALLBACK', 
            "Impressed by what you're building at {company_name}, particularly your approach in the {industry} space")
        
        icebreaker = fallback_template.format(
            company_name=lead.company_name,
            industry=lead.industry or "business",
            first_name=lead.first_name
        )
        
        return {
            'icebreaker': icebreaker,
            'company_name': lead.company_name,
            'status': 'fallback',
            'error': error,
            'provider': 'fallback',
            'generated_at': None
        }
    
    def test_connection(self) -> bool:
        """Test if n8n workflow is accessible"""
        test_lead = Lead(
            first_name="John",
            last_name="Test", 
            email="john@test.com",
            company_name="Test Company",
            industry="Testing",
            website="https://test.com",
            title="CEO"
        )
        
        logger.info("Testing n8n workflow connection...")
        result = self.generate_icebreaker(test_lead)
        
        if result.get('status') == 'success':
            logger.info("✅ n8n workflow connection successful")
            return True
        elif result.get('status') == 'fallback':
            logger.warning(f"⚠️ n8n workflow connection failed: {result.get('error', 'Unknown error')}")
            return False
        else:
            logger.warning("⚠️ n8n workflow returned unexpected response")
            return False
    
    def batch_generate_icebreakers(self, leads: list[Lead], max_concurrent: int = 5) -> list[Dict]:
        """
        Generate icebreakers for multiple leads
        
        Args:
            leads: List of Lead objects
            max_concurrent: Maximum concurrent requests (n8n rate limiting)
            
        Returns:
            List of icebreaker results
        """
        import concurrent.futures
        import time
        
        results = []
        
        # Process in batches to respect rate limits
        batch_size = max_concurrent
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i + batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} leads")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                future_to_lead = {
                    executor.submit(self.generate_icebreaker, lead): lead 
                    for lead in batch
                }
                
                for future in concurrent.futures.as_completed(future_to_lead):
                    lead = future_to_lead[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error processing {lead.company_name}: {e}")
                        results.append(self._get_fallback_response(lead, str(e)))
            
            # Rate limiting between batches
            if i + batch_size < len(leads):
                logger.info("Pausing between batches...")
                time.sleep(1)
        
        logger.info(f"Completed batch processing: {len(results)} icebreakers generated")
        return results

def main():
    """Test the n8n icebreaker client"""
    import sys
    
    print("🚀 n8n Claude Icebreaker Client Test")
    print("=" * 40)
    
    # Check if webhook URL is configured
    webhook_url = os.getenv('N8N_ICEBREAKER_WEBHOOK_URL')
    if not webhook_url:
        print("❌ N8N_ICEBREAKER_WEBHOOK_URL not configured in .env file")
        print("💡 Example: N8N_ICEBREAKER_WEBHOOK_URL=https://your-n8n-instance.com/webhook/claude-icebreaker")
        return
    
    try:
        client = N8nIcebreakerClient()
        
        # Test connection
        if not client.test_connection():
            print("❌ n8n workflow connection failed")
            return
        
        # Test with sample leads
        test_leads = [
            Lead("John", "Smith", "john@testcompany.com", "Test Marketing Agency", 
                 "Marketing", "https://testcompany.com", "CEO"),
            Lead("Jane", "Doe", "jane@consultech.com", "ConsuTech Solutions", 
                 "Consulting", "https://consultech.com", "Founder"),
            Lead("Bob", "Johnson", "bob@automate.co", "Automate Plus", 
                 "Automation", "https://automate.co", "CTO")
        ]
        
        print(f"\n🧪 Testing with {len(test_leads)} sample leads...")
        
        for i, lead in enumerate(test_leads, 1):
            print(f"\nTest {i}: {lead.company_name}")
            result = client.generate_icebreaker(lead)
            print(f"Status: {result['status']}")
            print(f"Icebreaker: {result['icebreaker']}")
            if result.get('error'):
                print(f"Error: {result['error']}")
        
        print("\n✅ n8n icebreaker testing complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()