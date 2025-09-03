#!/usr/bin/env python3
"""
Quick webhook test script for n8n Claude workflow
"""
import requests
import json

def test_webhook():
    webhook_url = 'https://spdery.app.n8n.cloud/webhook/generate-icebreaker'
    
    print('Testing n8n Claude Webhook')
    print('=' * 30)
    
    test_data = {
        'company_name': 'TechStart Solutions',
        'industry': 'SaaS',
        'first_name': 'Sarah', 
        'last_name': 'Johnson',
        'title': 'CEO',
        'website': 'https://techstart.com'
    }
    
    try:
        print('Making webhook call...')
        response = requests.post(webhook_url, json=test_data, timeout=30)
        
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200 and response.text.strip():
            result = json.loads(response.text)
            print(f'✓ SUCCESS!')
            print(f'Icebreaker: "{result.get("icebreaker", "")}"')
            print(f'Provider: {result.get("provider", "")}')
            
        elif response.status_code == 200:
            print('✗ Empty response - check n8n configuration')
            
        else:
            print(f'✗ Error {response.status_code}: {response.text}')
            
    except Exception as e:
        print(f'✗ Error: {e}')

if __name__ == '__main__':
    test_webhook()