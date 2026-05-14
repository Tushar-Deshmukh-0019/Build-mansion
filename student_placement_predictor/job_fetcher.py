"""
Job Recommendations Module
Fetches relevant jobs based on student's domain and confidence level
"""

import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Mock job data for demonstration (replace with real API later)
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


def get_jobs_for_domain(domain, confidence, limit=5):
    """
    Fetch jobs based on domain and confidence level
    
    Args:
        domain: Student's project domain
        confidence: Prediction confidence (0-1)
        limit: Number of jobs to return
    
    Returns:
        List of job dictionaries
    """
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
    
    # Sort by match score
    filtered_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    
    return filtered_jobs[:limit]


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


# For future: Real API integration
def fetch_from_linkedin_api(domain, location="India"):
    """
    Placeholder for LinkedIn API integration
    Requires LinkedIn API key and proper authentication
    """
    # TODO: Implement LinkedIn API integration
    pass


def fetch_from_indeed_api(domain, location="India"):
    """
    Placeholder for Indeed API integration
    Requires Indeed API key
    """
    # TODO: Implement Indeed API integration
    pass


def fetch_from_naukri_api(domain, location="India"):
    """
    Placeholder for Naukri API integration
    Requires Naukri API key
    """
    # TODO: Implement Naukri API integration
    pass
