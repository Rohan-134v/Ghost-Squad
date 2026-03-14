import datetime
import requests
import pytz

LEETCODE_URL = "https://leetcode.com/graphql"
IST = pytz.timezone('Asia/Kolkata')

def get_user_stats(username):
    """
    Fetches detailed stats: { 'solved_today': bool, 'total_solved': int, 'breakdown': [easy, med, hard] }
    """
    query = """
    query getUserProfile($username: String!) {
        matchedUser(username: $username) {
            submitStats {
                acSubmissionNum {
                    difficulty
                    count
                }
            }
        }
        recentSubmissionList(username: $username, limit: 1) {
            timestamp
            statusDisplay
        }
    }
    """
    variables = {'username': username}

    try:
        response = requests.post(LEETCODE_URL, json={'query': query, 'variables': variables}, timeout=10)
        data = response.json()
        
        if 'errors' in data or not data.get('data', {}).get('matchedUser'):
            return None

        # 1. Parse Total Solved Breakdown
        stats = data['data']['matchedUser']['submitStats']['acSubmissionNum']
        total_solved = next((item['count'] for item in stats if item['difficulty'] == 'All'), 0)
        easy = next((item['count'] for item in stats if item['difficulty'] == 'Easy'), 0)
        medium = next((item['count'] for item in stats if item['difficulty'] == 'Medium'), 0)
        hard = next((item['count'] for item in stats if item['difficulty'] == 'Hard'), 0)

        # 2. Check Daily Status
        solved_today = False
        recent = data['data']['recentSubmissionList']
        if recent:
            submission = recent[0]
            utc_time = datetime.datetime.fromtimestamp(int(submission['timestamp']), pytz.utc)
            submission_ist = utc_time.astimezone(IST)
            now_ist = datetime.datetime.now(IST)
            
            # Check if submission was today (IST) and Accepted
            if submission_ist.date() == now_ist.date() and submission['statusDisplay'] == 'Accepted':
                solved_today = True

        return {
            "solved_today": solved_today,
            "total_solved": total_solved,
            "breakdown": [easy, medium, hard]
        }
    
    except Exception as e:
        print(f"API error for {username}: {e}")
        return None

def check(username):
    """Legacy wrapper for backward compatibility"""
    stats = get_user_stats(username)
    return stats['solved_today'] if stats else False