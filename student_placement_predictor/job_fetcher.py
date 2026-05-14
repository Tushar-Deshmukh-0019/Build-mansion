"""
Job Recommendations Module
Fetches REAL jobs from Adzuna API based on student's domain and confidence level
"""

import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Adzuna API Configuration (Free tier: 1000 calls/month)
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search"

# Domain to search query mapping (simplified for better results)
DOMAIN_SEARCH_QUERIES = {
    "Web Development": "web developer",
    "Mobile App Development": "mobile developer",
    "Machine Learning": "machine learning",
    "Data Science": "data scientist",
    "Cloud Computing": "cloud engineer",
    "Cybersecurity": "security analyst",
    "CAD Design": "CAD designer",
    "Robotics": "robotics engineer",
    "IoT": "IoT developer",
    "General": "software engineer"
}


def fetch_real_jobs_from_adzuna(domain, confidence, limit=5):
    """
    Fetch REAL jobs from Adzuna API
    
    Args:
        domain: Student's project domain
        confidence: Prediction confidence (0-1)
        limit: Number of jobs to return
    
    Returns:
        List of real job dictionaries
    """
    # Check if API credentials are configured
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("[job_fetcher] ⚠️ Adzuna API credentials not configured. Using fallback.")
        return get_jobs_fallback(domain, confidence, limit)
    
    try:
        # Get search query for domain
        search_query = DOMAIN_SEARCH_QUERIES.get(domain, DOMAIN_SEARCH_QUERIES["General"])
        
        # Determine experience level based on confidence
        if confidence >= 0.75:
            experience_level = "mid level"
        elif confidence >= 0.50:
            experience_level = "entry level"
        else:
            experience_level = "entry level graduate"
        
        # Build API request
        url = f"{ADZUNA_BASE_URL}/1"  # Page 1
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": limit,
            "what": search_query,  # Simplified query works better
            "where": "India",  # Search all of India
            "sort_by": "relevance"
        }
        
        print(f"[job_fetcher] 🔍 Fetching real jobs for: {domain} ({experience_level})")
        print(f"[job_fetcher] 🔍 Search query: {search_query}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        print(f"[job_fetcher] 📊 API returned {len(results)} results")
        
        jobs = []
        
        for job_data in results[:limit]:
            # Calculate match score based on confidence and relevance
            base_score = 0.7 if confidence >= 0.75 else 0.6
            match_score = min(base_score + (confidence * 0.3), 1.0)
            
            # Extract company name
            company_data = job_data.get("company", {})
            if isinstance(company_data, dict):
                company_name = company_data.get("display_name", "Company")
            else:
                company_name = str(company_data) if company_data else "Company"
            
            # Extract location
            location_data = job_data.get("location", {})
            if isinstance(location_data, dict):
                location_name = location_data.get("display_name", "India")
            else:
                location_name = str(location_data) if location_data else "India"
            
            job = {
                "title": job_data.get("title", "N/A"),
                "company": company_name,
                "location": location_name,
                "url": job_data.get("redirect_url", "#"),
                "description": job_data.get("description", "")[:200] + "..." if job_data.get("description") else "No description available",
                "salary": job_data.get("salary_min", "Not specified"),
                "posted_date": job_data.get("created", "Recently"),
                "match_score": match_score,
                "domain": domain,
                "level": experience_level
            }
            jobs.append(job)
        
        if jobs:
            print(f"[job_fetcher] ✅ Fetched {len(jobs)} real jobs from Adzuna")
            return jobs
        else:
            print(f"[job_fetcher] ⚠️ No jobs found for {domain}, using fallback")
            return get_jobs_fallback(domain, confidence, limit)
        
    except requests.exceptions.RequestException as e:
        print(f"[job_fetcher] ❌ API Error: {e}")
        return get_jobs_fallback(domain, confidence, limit)
    except Exception as e:
        print(f"[job_fetcher] ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return get_jobs_fallback(domain, confidence, limit)


def get_jobs_fallback(domain, confidence, limit=5):
    """
    Fallback to web scraping or alternative free APIs if Adzuna fails
    Uses JSearch API (RapidAPI) as backup
    """
    try:
        # Try JSearch API (RapidAPI - free tier available)
        rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        
        if rapidapi_key:
            return fetch_from_jsearch_api(domain, confidence, limit, rapidapi_key)
        else:
            print("[job_fetcher] ⚠️ No backup API configured. Using mock data.")
            return get_mock_jobs_for_domain(domain, confidence, limit)
            
    except Exception as e:
        print(f"[job_fetcher] ❌ Fallback error: {e}")
        return get_mock_jobs_for_domain(domain, confidence, limit)


def fetch_from_jsearch_api(domain, confidence, limit, api_key):
    """
    Fetch jobs from JSearch API (RapidAPI)
    Free tier: 150 requests/month
    """
    try:
        search_query = DOMAIN_SEARCH_QUERIES.get(domain, DOMAIN_SEARCH_QUERIES["General"])
        
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {
            "query": f"{search_query} in India",
            "page": "1",
            "num_pages": "1",
            "date_posted": "month"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        jobs = []
        
        for job_data in data.get("data", [])[:limit]:
            match_score = min(0.7 + (confidence * 0.3), 1.0)
            
            job = {
                "title": job_data.get("job_title", "N/A"),
                "company": job_data.get("employer_name", "Company"),
                "location": job_data.get("job_city", "India"),
                "url": job_data.get("job_apply_link", "#"),
                "description": job_data.get("job_description", "")[:200] + "...",
                "salary": job_data.get("job_salary", "Not specified"),
                "posted_date": job_data.get("job_posted_at_datetime_utc", "Recently"),
                "match_score": match_score,
                "domain": domain,
                "level": "entry_level" if confidence < 0.75 else "mid_level"
            }
            jobs.append(job)
        
        print(f"[job_fetcher] ✅ Fetched {len(jobs)} jobs from JSearch API")
        return jobs
        
    except Exception as e:
        print(f"[job_fetcher] ❌ JSearch API error: {e}")
        return get_mock_jobs_for_domain(domain, confidence, limit)
def get_mock_jobs_for_domain(domain, confidence, limit=5):
    """
    Fallback mock data (only used if all APIs fail)
    """
    MOCK_JOBS = {
    "Web Development": [
        {"title": "Frontend Developer", "company": "Tech Corp", "location": "Bangalore", "url": "https://example.com/job1", "level": "entry"},
        {"title": "Full Stack Developer", "company": "StartupXYZ", "location": "Mumbai", "url": "https://example.com/job2", "level": "mid"},
        {"title": "React Developer", "company": "WebSolutions", "location": "Pune", "url": "https://example.com/job3", "level": "entry"},
        {"title": "Senior Web Developer", "company": "Digital Agency", "location": "Hyderabad", "url": "https://example.com/job4", "level": "senior"},
    ],
    "Mobile App Development": [
        {"title": "Android Developer", "company": "Mobile First", "location": "Bangalore", "url": "https://example.com/job5", "level": "entry"},
        {"title": "iOS Developer", "company": "App Studio", "location": "Delhi", "url": "https://example.com/job6", "level": "mid"},
        {"title": "Flutter Developer", "company": "CrossPlatform Inc", "location": "Chennai", "url": "https://example.com/job7", "level": "entry"},
    ],
    "Machine Learning": [
        {"title": "ML Engineer", "company": "AI Labs", "location": "Bangalore", "url": "https://example.com/job8", "level": "mid"},
        {"title": "Data Scientist", "company": "Analytics Co", "location": "Mumbai", "url": "https://example.com/job9", "level": "entry"},
        {"title": "AI Research Intern", "company": "Research Institute", "location": "Hyderabad", "url": "https://example.com/job10", "level": "entry"},
    ],
    "Data Science": [
        {"title": "Data Analyst", "company": "DataCorp", "location": "Pune", "url": "https://example.com/job11", "level": "entry"},
        {"title": "Business Intelligence Analyst", "company": "BI Solutions", "location": "Bangalore", "url": "https://example.com/job12", "level": "entry"},
        {"title": "Senior Data Scientist", "company": "Big Data Inc", "location": "Mumbai", "url": "https://example.com/job13", "level": "senior"},
    ],
    "Cloud Computing": [
        {"title": "Cloud Engineer", "company": "CloudTech", "location": "Bangalore", "url": "https://example.com/job14", "level": "mid"},
        {"title": "AWS Developer", "company": "Cloud Solutions", "location": "Hyderabad", "url": "https://example.com/job15", "level": "entry"},
        {"title": "DevOps Engineer", "company": "Infrastructure Co", "location": "Pune", "url": "https://example.com/job16", "level": "mid"},
    ],
    "Cybersecurity": [
        {"title": "Security Analyst", "company": "SecureNet", "location": "Delhi", "url": "https://example.com/job17", "level": "entry"},
        {"title": "Penetration Tester", "company": "CyberDefense", "location": "Bangalore", "url": "https://example.com/job18", "level": "mid"},
    ],
    "CAD Design": [
        {"title": "CAD Designer", "company": "Engineering Firm", "location": "Pune", "url": "https://example.com/job19", "level": "entry"},
        {"title": "Mechanical Designer", "company": "AutoCAD Solutions", "location": "Chennai", "url": "https://example.com/job20", "level": "entry"},
    ],
    "Robotics": [
        {"title": "Robotics Engineer", "company": "RoboTech", "location": "Bangalore", "url": "https://example.com/job21", "level": "mid"},
        {"title": "Automation Engineer", "company": "Industrial Automation", "location": "Mumbai", "url": "https://example.com/job22", "level": "entry"},
    ],
    "IoT": [
        {"title": "IoT Developer", "company": "Smart Devices", "location": "Bangalore", "url": "https://example.com/job23", "level": "entry"},
        {"title": "Embedded Systems Engineer", "company": "IoT Solutions", "location": "Hyderabad", "url": "https://example.com/job24", "level": "mid"},
    ],
    "General": [
        {"title": "Software Engineer", "company": "Tech Company", "location": "Bangalore", "url": "https://example.com/job25", "level": "entry"},
        {"title": "IT Support Specialist", "company": "IT Services", "location": "Mumbai", "url": "https://example.com/job26", "level": "entry"},
    ]
}
    
    # Determine job level based on confidence
    if confidence >= 0.75:
        preferred_levels = ["mid", "senior", "entry"]
    elif confidence >= 0.50:
        preferred_levels = ["entry", "mid"]
    else:
        preferred_levels = ["entry"]
    
    # Get jobs for domain
    domain_jobs = MOCK_JOBS.get(domain, MOCK_JOBS["General"])
    
    # Filter by level
    filtered_jobs = [
        job.copy() for job in domain_jobs 
        if job["level"] in preferred_levels
    ]
    
    # If not enough jobs, add from general
    if len(filtered_jobs) < limit:
        general_jobs = [j.copy() for j in MOCK_JOBS["General"] if j not in filtered_jobs]
        filtered_jobs.extend(general_jobs[:limit - len(filtered_jobs)])
    
    # Calculate match score and add domain
    for job in filtered_jobs:
        if job["level"] == "entry":
            base_score = 0.7
        elif job["level"] == "mid":
            base_score = 0.8
        else:
            base_score = 0.9
        
        # Adjust by confidence
        job["match_score"] = min(base_score + (confidence * 0.2), 1.0)
        
        # Add domain field
        job["domain"] = domain
        job["description"] = f"Position for {job['title']} at {job['company']}"
        job["salary"] = "As per industry standards"
        job["posted_date"] = "Recently"
    
    # Sort by match score
    filtered_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    
    print(f"[job_fetcher] ⚠️ Using mock data fallback for {domain}")
    return filtered_jobs[:limit]


def get_jobs_for_domain(domain, confidence, limit=5):
    """
    Main function to fetch jobs - tries real APIs first, falls back to mock data
    
    Args:
        domain: Student's project domain
        confidence: Prediction confidence (0-1)
        limit: Number of jobs to return
    
    Returns:
        List of job dictionaries (real or mock)
    """
    # Try to fetch real jobs from Adzuna API
    return fetch_real_jobs_from_adzuna(domain, confidence, limit)


def save_job_recommendations(conn, user_id, jobs):
    """Save job recommendations to database"""
    try:
        cursor = conn.cursor()
        
        for job in jobs:
            cursor.execute("""
                INSERT INTO job_recommendations
                    (user_id, job_title, company, domain, location, job_url, match_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                job["title"],
                job["company"],
                job.get("domain", "General"),
                job["location"],
                job["url"],
                job["match_score"]
            ))
        
        conn.commit()
        print(f"[job_fetcher] Saved {len(jobs)} job recommendations for user {user_id}")
        return True
        
    except Exception as e:
        print(f"[job_fetcher] Error saving jobs: {e}")
        conn.rollback()
        return False


def get_user_job_recommendations(conn, user_id, limit=10):
    """Get saved job recommendations for a user"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_title, company, domain, location, job_url, match_score, created_at
            FROM job_recommendations
            WHERE user_id = %s
            ORDER BY match_score DESC, created_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        
        jobs = []
        for row in rows:
            jobs.append({
                "title": row[0],
                "company": row[1],
                "domain": row[2],
                "location": row[3],
                "url": row[4],
                "match_score": row[5],
                "created_at": row[6]
            })
        
        return jobs
        
    except Exception as e:
        print(f"[job_fetcher] Error fetching jobs: {e}")
        return []


# ==========================================
# API SETUP INSTRUCTIONS
# ==========================================
"""
To use REAL job data, sign up for free API keys:

1. ADZUNA API (Recommended - 1000 calls/month free):
   - Sign up: https://developer.adzuna.com/signup
   - Get your App ID and App Key
   - Add to .env file:
     ADZUNA_APP_ID=your_app_id_here
     ADZUNA_APP_KEY=your_app_key_here

2. JSEARCH API (Backup - 150 calls/month free):
   - Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
   - Subscribe to free tier
   - Get your RapidAPI key
   - Add to .env file:
     RAPIDAPI_KEY=your_rapidapi_key_here

If no API keys are configured, the system will use mock data as fallback.
"""
