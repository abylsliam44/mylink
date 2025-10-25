"""
HR Knowledge Base
Pre-populated knowledge for better RAG responses
"""
from typing import List, Dict, Any

# HR Best Practices Knowledge
HR_KNOWLEDGE = [
    {
        "category": "interview_questions",
        "text": """
        Вопросы для технических интервью:
        1. Расскажите о вашем опыте работы с [технология]
        2. Как вы решали сложные технические задачи?
        3. Опишите проект, которым вы гордитесь
        4. Как вы изучаете новые технологии?
        5. Расскажите о вашем подходе к тестированию кода
        """
    },
    {
        "category": "soft_skills",
        "text": """
        Мягкие навыки для IT специалистов:
        - Коммуникативные навыки
        - Работа в команде
        - Адаптивность к изменениям
        - Решение проблем
        - Лидерские качества
        - Тайм-менеджмент
        """
    },
    {
        "category": "salary_benchmarks",
        "text": """
        Зарплатные вилки в Казахстане (2024):
        - Junior Developer: 200,000 - 400,000 KZT
        - Middle Developer: 400,000 - 700,000 KZT
        - Senior Developer: 700,000 - 1,200,000 KZT
        - Team Lead: 1,000,000 - 1,500,000 KZT
        - Project Manager: 500,000 - 900,000 KZT
        """
    },
    {
        "category": "tech_skills",
        "text": """
        Популярные технологии в Казахстане:
        - Frontend: React, Vue.js, Angular, TypeScript
        - Backend: Python, Node.js, Java, C#
        - Mobile: React Native, Flutter, Swift, Kotlin
        - DevOps: Docker, Kubernetes, AWS, Azure
        - Data: Python, SQL, Machine Learning, AI
        """
    },
    {
        "category": "interview_tips",
        "text": """
        Советы для проведения интервью:
        1. Подготовьте структурированные вопросы
        2. Слушайте внимательно ответы кандидата
        3. Задавайте уточняющие вопросы
        4. Оценивайте не только технические, но и мягкие навыки
        5. Дайте кандидату возможность задать вопросы
        6. Будьте вежливы и профессиональны
        """
    },
    {
        "category": "red_flags",
        "text": """
        Красные флаги в резюме:
        - Неточные даты работы
        - Противоречивая информация
        - Отсутствие конкретных достижений
        - Слишком общие формулировки
        - Нереалистичные требования к зарплате
        - Негативные отзывы о предыдущих работодателях
        """
    },
    {
        "category": "company_culture",
        "text": """
        Корпоративная культура в IT:
        - Гибкий график работы
        - Возможность удаленной работы
        - Обучение и развитие
        - Современные технологии
        - Командная работа
        - Инновации и креативность
        """
    }
]

# IT Skills Taxonomy
IT_SKILLS_TAXONOMY = [
    {
        "category": "programming_languages",
        "skills": [
            "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust",
            "PHP", "Ruby", "Swift", "Kotlin", "Scala", "Clojure", "Haskell"
        ]
    },
    {
        "category": "web_frameworks",
        "skills": [
            "React", "Vue.js", "Angular", "Svelte", "Next.js", "Nuxt.js",
            "Django", "Flask", "FastAPI", "Express.js", "NestJS", "Spring Boot"
        ]
    },
    {
        "category": "databases",
        "skills": [
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
            "Cassandra", "DynamoDB", "SQLite", "Oracle", "SQL Server"
        ]
    },
    {
        "category": "cloud_platforms",
        "skills": [
            "AWS", "Azure", "Google Cloud", "DigitalOcean", "Heroku",
            "Vercel", "Netlify", "Firebase", "Supabase"
        ]
    },
    {
        "category": "devops_tools",
        "skills": [
            "Docker", "Kubernetes", "Jenkins", "GitLab CI", "GitHub Actions",
            "Terraform", "Ansible", "Prometheus", "Grafana", "ELK Stack"
        ]
    },
    {
        "category": "mobile_development",
        "skills": [
            "React Native", "Flutter", "Ionic", "Xamarin", "Cordova",
            "Swift", "Kotlin", "Objective-C", "Java (Android)"
        ]
    }
]

# Interview Questions Database
INTERVIEW_QUESTIONS = [
    {
        "category": "technical_python",
        "questions": [
            "Расскажите о различиях между списками и кортежами в Python",
            "Что такое декораторы и как их использовать?",
            "Объясните принципы ООП в Python",
            "Как работает garbage collection в Python?",
            "Что такое GIL и как это влияет на многопоточность?"
        ]
    },
    {
        "category": "technical_react",
        "questions": [
            "В чем разница между функциональными и классовыми компонентами?",
            "Объясните жизненный цикл компонента React",
            "Что такое hooks и как их использовать?",
            "Как оптимизировать производительность React приложения?",
            "Расскажите о state management в React"
        ]
    },
    {
        "category": "system_design",
        "questions": [
            "Как бы вы спроектировали систему для обработки 1 млн запросов в день?",
            "Объясните принципы микросервисной архитектуры",
            "Как обеспечить высокую доступность системы?",
            "Что такое load balancing и зачем он нужен?",
            "Как бы вы масштабировали базу данных?"
        ]
    },
    {
        "category": "behavioral",
        "questions": [
            "Расскажите о сложной задаче, которую вы решили",
            "Как вы работаете в команде?",
            "Опишите ситуацию, когда вы учились новой технологии",
            "Как вы справляетесь с конфликтами в команде?",
            "Расскажите о ваших карьерных целях"
        ]
    }
]

def get_hr_knowledge() -> List[Dict[str, Any]]:
    """Get all HR knowledge entries"""
    return HR_KNOWLEDGE

def get_it_skills_taxonomy() -> List[Dict[str, Any]]:
    """Get IT skills taxonomy"""
    return IT_SKILLS_TAXONOMY

def get_interview_questions() -> List[Dict[str, Any]]:
    """Get interview questions database"""
    return INTERVIEW_QUESTIONS

def get_skills_by_category(category: str) -> List[str]:
    """Get skills by category"""
    for skill_group in IT_SKILLS_TAXONOMY:
        if skill_group["category"] == category:
            return skill_group["skills"]
    return []

def get_questions_by_category(category: str) -> List[str]:
    """Get questions by category"""
    for question_group in INTERVIEW_QUESTIONS:
        if question_group["category"] == category:
            return question_group["questions"]
    return []
