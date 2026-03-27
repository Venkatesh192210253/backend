import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myfitnessbuddy_backend.settings')
django.setup()

from support.models import FAQ

faqs = [
    {
        "question": "How do I track my steps?",
        "answer": "My Fitness Buddy automatically tracks your steps using your phone's motion sensors. Just keep your phone with you while you walk!",
        "order": 1
    },
    {
        "question": "How do I earn XP?",
        "answer": "You earn XP by logging meals (+10 XP), recording workouts (+50 XP), completing challenges (+200 XP), and making new friends (+100 XP).",
        "order": 2
    },
    {
        "question": "What is the AI Coach?",
        "answer": "The AI Coach is your personal fitness assistant. It analyzes your activity, diet, and goals to provide personalized advice and motivation.",
        "order": 3
    },
    {
        "question": "Can I sync with other devices?",
        "answer": "Currently, we use your phone's built-in sensors. We are working on integration with Google Fit and other wearable devices in future updates.",
        "order": 4
    },
    {
        "question": "Is my data private?",
        "answer": "Yes, your privacy is our priority. You can manage what data is shared with friends in the Privacy Settings section of your profile.",
        "order": 5
    }
]

for faq_data in faqs:
    faq, created = FAQ.objects.get_or_create(
        question=faq_data["question"],
        defaults={"answer": faq_data["answer"], "order": faq_data["order"]}
    )
    if created:
        print(f"Created FAQ: {faq.question}")
    else:
        print(f"FAQ already exists: {faq.question}")

print("Default FAQs setup completed.")
