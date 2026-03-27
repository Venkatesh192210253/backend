from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.http import HttpResponse
from .models import FAQ, SupportTicket
from .serializers import FAQSerializer, SupportTicketSerializer

class FAQListView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        faqs = FAQ.objects.all()
        # If no FAQs exist, create some defaults
        if not faqs.exists():
            FAQ.objects.create(question="How do I track my meals?", answer="Go to the 'Food' tab and tap 'Add Meal'.", order=1)
            FAQ.objects.create(question="How do I add friends?", answer="Go to the social section and search for users.", order=2)
            faqs = FAQ.objects.all()
        
        serializer = FAQSerializer(faqs, many=True)
        return Response(serializer.data)

class TicketCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SupportTicketSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def terms_of_service(request):
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Terms of Service | My Fitness Buddy</title>
        <style>
            :root {
                --primary: #00C896;
                --primary-dark: #00A67E;
                --text-main: #1F2937;
                --text-light: #6B7280;
                --bg: #F8FAF9;
            }
            body { 
                font-family: 'Inter', -apple-system, sans-serif; 
                line-height: 1.6; 
                color: var(--text-main); 
                background-color: var(--bg);
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 800px;
                margin: 40px auto;
                padding: 40px;
                background: white;
                box-shadow: 0 10px 25px rgba(0,0,0,0.05);
                border-radius: 24px;
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            h1 { color: var(--text-main); font-size: 2.5rem; margin-bottom: 10px; }
            h2 { color: var(--primary); font-size: 1.5rem; margin-top: 30px; border-bottom: 2px solid #F0F0F0; padding-bottom: 10px; }
            p { margin-bottom: 20px; color: var(--text-light); }
            .update-date { font-size: 0.9rem; color: var(--text-light); font-style: italic; }
            @media (max-width: 600px) {
                .container { margin: 10px; padding: 20px; border-radius: 16px; }
                h1 { font-size: 1.8rem; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Terms of Service</h1>
                <p class="update-date">Last Updated: March 17, 2026</p>
            </div>
            
            <p>Welcome to <strong>My Fitness Buddy</strong>. By using our application, services, and website, you agree to comply with and be bound by the following terms and conditions.</p>
            
            <h2>1. Acceptance of Terms</h2>
            <p>By creating an account or using My Fitness Buddy, you agree to these legal terms. If you do not agree to all terms, do not use the application.</p>
            
            <h2>2. User Responsibility</h2>
            <p>You are responsible for maintaining the security of your account and password. You are solely responsible for all activities that occur under your account.</p>
            
            <h2>3. Medical Disclaimer</h2>
            <p>My Fitness Buddy is a tool for tracking and motivation. It does NOT provide medical advice. Always consult with a qualified healthcare professional before starting any new diet or exercise program.</p>
            
            <h2>4. Intellectual Property</h2>
            <p>The app's design, code, and original content are the property of My Fitness Buddy and are protected by copyright laws.</p>
            
            <h2>5. Termination</h2>
            <p>We reserve the right to suspend or terminate your account at our sole discretion, without notice, for behavior that violates these terms.</p>
            
            <div style="margin-top: 50px; text-align: center; border-top: 1px solid #EEE; padding-top: 20px;">
                <p>&copy; 2026 My Fitness Buddy. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

def privacy_policy(request):
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Privacy Policy | My Fitness Buddy</title>
        <style>
            :root {
                --primary: #00C896;
                --text-main: #1F2937;
                --text-light: #6B7280;
                --bg: #F8FAF9;
            }
            body { 
                font-family: 'Inter', -apple-system, sans-serif; 
                line-height: 1.6; 
                color: var(--text-main); 
                background-color: var(--bg);
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 800px;
                margin: 40px auto;
                padding: 40px;
                background: white;
                box-shadow: 0 10px 25px rgba(0,0,0,0.05);
                border-radius: 24px;
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            h1 { color: var(--text-main); font-size: 2.5rem; }
            h2 { color: var(--primary); font-size: 1.5rem; margin-top: 30px; }
            p { margin-bottom: 20px; color: var(--text-light); }
            @media (max-width: 600px) {
                .container { margin: 10px; padding: 20px; }
                h1 { font-size: 1.8rem; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Privacy Policy</h1>
                <p>Your privacy is our priority.</p>
            </div>
            
            <h2>1. Information We Collect</h2>
            <p>We collect data you provide: profile details (age, weight, height), nutrition logs, and activity data synced from your device sensors.</p>
            
            <h2>2. Data Usage</h2>
            <p>We use your data strictly to calculate your health metrics, provide AI-driven suggestions, and track your fitness progress.</p>
            
            <h2>3. Security</h2>
            <p>We implement industry-standard encryption and security measures to protect your personal data and sensitive information.</p>
            
            <h2>4. Third-Party Sharing</h2>
            <p>We do NOT sell your personal data. We only share data with third parties when necessary for core app functionality or when explicitly authorized by you.</p>
            
            <h2>5. Your Rights</h2>
            <p>You can request a copy of your data or deletion of your account at any time through the profile settings in the app.</p>
            
            <div style="margin-top: 50px; text-align: center; border-top: 1px solid #EEE; padding-top: 20px;">
                <p>&copy; 2026 My Fitness Buddy. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)
