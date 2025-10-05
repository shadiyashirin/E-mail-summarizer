import os
import json
import re
import time
import google.generativeai as genai
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import EmailSummary, EmailResult

def home(request):
    """Home page with features and introduction"""
    # Get some stats for the home page
    total_summaries = EmailSummary.objects.count()
    total_emails = EmailResult.objects.count()
    
    context = {
        'total_summaries': total_summaries,
        'total_emails': total_emails,
    }
    
    return render(request, 'summarizer/home.html', context)

@require_http_methods(["GET", "POST"])
def upload_emails(request):
    """Handle email file upload and processing"""
    print("=" * 50)
    print("📨 UPLOAD_EMAILS VIEW CALLED")
    print(f"📨 Request method: {request.method}")
    
    if request.method == 'POST':
        print("✅ POST request received")
        print(f"✅ Files available: {list(request.FILES.keys())}")
        print(f"✅ POST data: {list(request.POST.keys())}")
        
        if not request.FILES.get('email_file'):
            print("❌ No email_file found in FILES")
            return render(request, 'summarizer/upload.html', {
                'error': 'Please select a file to upload'
            })
        
        email_file = request.FILES['email_file']
        print(f"✅ File received - Name: {email_file.name}, Size: {email_file.size}, Type: {email_file.content_type}")
        
        # Validate file type
        if not email_file.name.endswith('.txt'):
            return render(request, 'summarizer/upload.html', {
                'error': 'Please upload a .txt file'
            })
        
        try:
            # Save the uploaded file
            print("💾 Saving file to database...")
            email_summary = EmailSummary.objects.create(email_file=email_file)
            print(f"✅ File saved with ID: {email_summary.id}")
            
            # Check if file actually exists in filesystem
            file_path = email_summary.email_file.path
            print(f"📁 File path: {file_path}")
            print(f"📁 File exists: {os.path.exists(file_path)}")
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ File saved successfully - Size: {file_size} bytes")
                
                # Read first few lines to verify content
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_lines = ''.join([f.readline() for _ in range(5)])
                print(f"📄 File content preview:\n{first_lines}")
            else:
                print("❌ File was not saved to filesystem!")
                raise Exception("File was not saved to filesystem")
            
            # Process the email file
            print("🔄 Starting email processing...")
            summaries = process_email_file(file_path)
            print(f"✅ Processing complete. Got {len(summaries)} summaries")
            
            # Save results to database
            for i, summary_data in enumerate(summaries):
                EmailResult.objects.create(
                    email_summary=email_summary,
                    sender=summary_data.get('sender', 'Unknown'),
                    subject=summary_data.get('subject', 'No Subject'),
                    summary=summary_data.get('summary', [])
                )
                print(f"📧 Saved result {i+1}: {summary_data.get('subject', 'No Subject')}")
            
            email_summary.processed = True
            email_summary.save()
            
            print(f"✅ Redirecting to results page: {email_summary.id}")
            return redirect('results', summary_id=email_summary.id)
            
        except Exception as e:
            print(f"❌ Error occurred: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            # Clean up if error occurs
            if 'email_summary' in locals():
                email_summary.delete()
            return render(request, 'summarizer/upload.html', {
                'error': f'Error processing file: {str(e)}'
            })
    
    print("📨 GET request - showing upload form")
    return render(request, 'summarizer/upload.html')


def results_view(request, summary_id):
    """Display email summaries - THIS WAS MISSING"""
    email_summary = get_object_or_404(EmailSummary, id=summary_id)
    email_results = email_summary.results.all()
    
    context = {
        'email_summary': email_summary,
        'email_results': email_results,
    }
    
    return render(request, 'summarizer/results.html', context)

def process_email_file(file_path):
    """Process email file and return summaries"""
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
    except Exception as e:
        return [{"error": f"Model setup failed: {e}"}]
    
    def read_emails(file_path):
        """Read and split email file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by separator lines
            emails = re.split(r'\n-{3,}\n', content)
            emails = [email.strip() for email in emails if email.strip()]
            return emails
        except Exception as e:
            raise Exception(f"Error reading file: {e}")
    
    def summarize_email(email_text, model):
        """Summarize a single email"""
        sender = "Unknown"
        subject = "No Subject"
        
        # Extract sender and subject
        sender_match = re.search(r'From:\s*(.+)', email_text)
        if sender_match:
            sender = sender_match.group(1).strip()
        
        subject_match = re.search(r'Subject:\s*(.+)', email_text)
        if subject_match:
            subject = subject_match.group(1).strip()
        
        prompt = f"""
Analyze this email and return JSON with: sender, subject, and 3-4 bullet points summary.

Email:
{email_text}

Return ONLY valid JSON.
"""
        
        try:
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return {
                    "sender": sender,
                    "subject": subject,
                    "summary": [f"Summary: {response_text[:150]}..."]
                }
                
        except Exception as e:
            return {
                "sender": sender,
                "subject": subject,
                "summary": [f"Error: {str(e)}"]
            }
    
    try:
        emails = read_emails(file_path)
        emails=emails[:5]
        results = []
        
        for i, email in enumerate(emails):
            summary = summarize_email(email, model)
            results.append(summary)
            
            # Rate limiting
            if i < len(emails) - 1:
                time.sleep(2)
        
        return results
        
    except Exception as e:
        return [{"error": f"Processing failed: {e}"}]

@csrf_exempt
@require_http_methods(["POST"])
def api_summarize(request):
    """API endpoint for single email summarization"""
    email_text = request.POST.get('email_text', '').strip()
    
    if not email_text:
        return JsonResponse({'error': 'No email text provided'}, status=400)
    
    try:
        summary = summarize_single_email(email_text)
        return JsonResponse(summary)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def summarize_single_email(email_text):
    """Summarize single email text"""
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        
        sender = "Unknown"
        subject = "No Subject"
        
        sender_match = re.search(r'From:\s*(.+)', email_text)
        if sender_match:
            sender = sender_match.group(1).strip()
        
        subject_match = re.search(r'Subject:\s*(.+)', email_text)
        if subject_match:
            subject = subject_match.group(1).strip()
        
        prompt = f"""
Analyze this email and return JSON with: sender, subject, and 3-4 bullet points summary.

Email:
{email_text}

Return ONLY valid JSON.
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {
                "sender": sender,
                "subject": subject,
                "summary": [f"Summary: {response_text[:150]}..."]
            }
            
    except Exception as e:
        return {
            "sender": "Error",
            "subject": "Error",
            "summary": [f"Error: {str(e)}"]
        }