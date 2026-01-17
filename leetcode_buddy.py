import datetime
import requests
import pytz

LEETCODE_URL = "https://leetcode.com/graphql"
IST = pytz.timezone('Asia/Kolkata')

def check(username):
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
            title
            timestamp
            statusDisplay
        }
    }
    """
    variables = {'username': username}

    try:
        response = requests.post(LEETCODE_URL, json={'query': query, 'variables': variables}, timeout=10)
        if response.status_code != 200:
            return False
            
        data = response.json()
        if 'errors' in data or not data.get('data', {}).get('recentSubmissionList'):
            return False
        
        submission = data['data']['recentSubmissionList'][0]
        
        utc_time = datetime.datetime.fromtimestamp(int(submission['timestamp']), pytz.utc)
        submission_ist = utc_time.astimezone(IST)
        now_ist = datetime.datetime.now(IST)
        
        is_same_day = submission_ist.date() == now_ist.date()
        is_accepted = submission['statusDisplay'] == 'Accepted'
        
        return is_same_day and is_accepted
    
    except Exception as e:
        print(f"API error: {e}")
        return False

