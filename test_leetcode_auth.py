import requests
import json
from datetime import datetime
import time
from typing import List, Dict, Optional, Any
import sys
from collections import defaultdict





class LeetCodeSubmissionFetcher:
    """Enhanced LeetCode submission fetcher with comprehensive data collection"""
    
    def __init__(self):
        self.session = None
        self.rate_limit_delay = 1.0
        self.max_retries = 3
        self.debug_mode = False
    
    def extract_cookies_manual(self) -> Dict[str, str]:
        """Manual cookie input method with validation"""
        print("=== LeetCode Cookie Extraction ===")
        print("1. Go to leetcode.com and log in")
        print("2. Open Developer Tools (F12)")
        print("3. Go to Application/Storage > Cookies > https://leetcode.com")
        print("4. Copy the values below:\n")
        
        session_cookie = input("Enter LEETCODE_SESSION value: ").strip()
        csrf_token = input("Enter csrftoken value (optional): ").strip()
        
        if not session_cookie:
            raise ValueError("LEETCODE_SESSION is required!")
        
        cookies = {'LEETCODE_SESSION': session_cookie}
        if csrf_token:
            cookies['csrftoken'] = csrf_token
            
        return cookies

    def create_authenticated_session(self, cookies: Dict[str, str]) -> requests.Session:
        """Create session with LeetCode authentication"""
        session = requests.Session()
        
        # Set cookies
        session.cookies.update(cookies)
        
        # Set required headers
        headers = {
            'Referer': 'https://leetcode.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Origin': 'https://leetcode.com'
        }
        
        if 'csrftoken' in cookies:
            headers['X-CSRFToken'] = cookies['csrftoken']
        
        session.headers.update(headers)
        self.session = session
        return session

    def test_authentication(self) -> bool:
        """Test authentication using GraphQL whoami query"""
        print("\n=== Testing Authentication ===")
        
        whoami_query = {
            "query": """
            query globalData {
                userStatus {
                    isSignedIn
                    username
                    realName
                    avatar
                    isPremium
                }
            }
            """,
            "operationName": "globalData"
        }
        
        try:
            response = self.session.post(
                'https://leetcode.com/graphql',
                json=whoami_query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"❌ GraphQL errors: {data['errors']}")
                    return False
                
                user_status = data.get('data', {}).get('userStatus', {})
                if user_status.get('isSignedIn'):
                    username = user_status.get('username', 'Unknown')
                    print(f"✅ Authentication successful!")
                    print(f"   Logged in as: {username}")
                    print(f"   Premium: {'Yes' if user_status.get('isPremium') else 'No'}")
                    return True
                else:
                    print("❌ Not signed in. Please check your session cookie.")
                    return False
            else:
                print(f"❌ Authentication failed. Status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False

    def fix_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Enhanced timestamp parsing with multiple format support"""
        if not timestamp:
            return None
            
        try:
            # Convert to int
            ts = int(timestamp)
            
            # Handle different timestamp formats
            current_time = time.time()
            
            # If timestamp is in milliseconds, convert to seconds
            if ts > 10000000000:
                ts = ts // 1000
            
            # If timestamp is still in the future, it might need adjustment
            if ts > current_time:
                # Try different epoch adjustments
                possible_adjustments = [
                    1577836800,  # 2020-01-01
                    1609459200,  # 2021-01-01
                    1640995200,  # 2022-01-01
                    1672531200,  # 2023-01-01
                    1704067200,  # 2024-01-01
                ]
                
                for adjustment in possible_adjustments:
                    adjusted_ts = ts - adjustment
                    if 946684800 <= adjusted_ts <= current_time:  # Between 2000 and now
                        ts = adjusted_ts
                        break
            
            # Final validation - timestamp should be reasonable
            if 946684800 <= ts <= current_time:  # Between 2000 and now
                return datetime.fromtimestamp(ts)
            else:
                if self.debug_mode:
                    print(f"   Debug: Invalid timestamp {timestamp} -> {ts}")
                return None
                
        except (ValueError, OSError) as e:
            if self.debug_mode:
                print(f"   Debug: Timestamp parsing error for {timestamp}: {e}")
            return None

    def fetch_recent_submissions(self, username: str, limit: int = 20) -> List[Dict]:
        """Fetch recent accepted submissions using GraphQL"""
        
        submissions_query = {
            "query": """
            query recentAcSubmissions($username: String!, $limit: Int!) {
                recentAcSubmissionList(username: $username, limit: $limit) {
                    id
                    title
                    titleSlug
                    timestamp
                    statusDisplay
                    lang
                    runtime
                    url
                    isPending
                    memory
                    topicTags {
                        name
                        slug
                    }
                }
            }
            """,
            "variables": {
                "username": username,
                "limit": limit
            },
            "operationName": "recentAcSubmissions"
        }
        
        try:
            response = self.session.post(
                'https://leetcode.com/graphql',
                json=submissions_query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"❌ GraphQL errors: {data['errors']}")
                    return []
                
                submissions = data.get('data', {}).get('recentAcSubmissionList', [])
                
                # Add source marker
                for sub in submissions:
                    sub['_source'] = 'graphql'
                    
                return submissions
            else:
                print(f"❌ Submissions request failed. Status: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error fetching submissions: {e}")
            return []

    def fetch_submission_history_rest(self, offset: int = 0, limit: int = 20) -> List[Dict]:
        """Fetch submissions using REST API"""
        
        try:
            url = f'https://leetcode.com/api/submissions/?offset={offset}&limit={limit}&lastkey='
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                submissions = data.get('submissions_dump', [])
                
                # Add source marker
                for sub in submissions:
                    sub['_source'] = 'rest'
                    
                return submissions
            else:
                return []
                
        except Exception as e:
            if self.debug_mode:
                print(f"❌ REST API error: {e}")
            return []

    def fetch_language_statistics(self, username: str) -> Dict[str, Any]:
        """Fetch language-wise problem statistics"""
        
        lang_query = {
            "query": """
            query languageStats($username: String!) {
                matchedUser(username: $username) {
                    languageProblemCount {
                        languageName
                        problemsSolved
                    }
                }
            }
            """,
            "variables": {"username": username},
            "operationName": "languageStats"
        }
        
        try:
            response = self.session.post(
                'https://leetcode.com/graphql',
                json=lang_query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    return {}
                
                user_data = data.get('data', {}).get('matchedUser', {})
                return user_data.get('languageProblemCount', [])
            
        except Exception as e:
            if self.debug_mode:
                print(f"❌ Language stats error: {e}")
            
        return []

    def smart_merge_submissions(self, graphql_subs: List[Dict], rest_subs: List[Dict]) -> List[Dict]:
        """Intelligently merge submissions from different sources, avoiding duplicates"""
        
        print("🔄 Smart merging submissions from multiple sources...")
        
        # Create a comprehensive deduplication strategy
        merged_submissions = []
        seen_submissions = set()
        
        # Priority: GraphQL submissions first (more reliable for accepted solutions)
        print(f"   Processing {len(graphql_subs)} GraphQL submissions...")
        for sub in graphql_subs:
            # Create unique key based on multiple fields
            key = (
                sub.get('titleSlug', ''),
                sub.get('lang', ''),
                sub.get('timestamp', ''),
                sub.get('statusDisplay', '')
            )
            
            if key not in seen_submissions and any(key):  # At least one field must be non-empty
                seen_submissions.add(key)
                merged_submissions.append(sub)
        
        # Add REST submissions that aren't duplicates
        print(f"   Processing {len(rest_subs)} REST API submissions...")
        added_from_rest = 0
        for sub in rest_subs:
            # Create key for REST submission
            key = (
                sub.get('title_slug', sub.get('titleSlug', '')),
                sub.get('lang', ''),
                sub.get('timestamp', ''),
                sub.get('status_display', sub.get('statusDisplay', ''))
            )
            
            if key not in seen_submissions and any(key):
                seen_submissions.add(key)
                merged_submissions.append(sub)
                added_from_rest += 1
        
        print(f"   ✓ Merged result: {len(merged_submissions)} unique submissions")
        print(f"   ✓ GraphQL contributed: {len(graphql_subs)}")
        print(f"   ✓ REST API contributed: {added_from_rest}")
        
        return merged_submissions

    def fetch_comprehensive_data(self, username: str) -> List[Dict]:
        """Comprehensive data fetching using multiple strategies"""
        print("\n=== Comprehensive Data Fetching ===")
        
        all_submissions = []
        
        # Strategy 1: GraphQL Recent Accepted (Higher limit)
        print("📄 Fetching GraphQL recent accepted submissions...")
        try:
            graphql_accepted = self.fetch_recent_submissions(username, limit=200)
            if graphql_accepted:
                print(f"   ✓ Found {len(graphql_accepted)} recent accepted submissions")
                all_submissions.extend(graphql_accepted)
            else:
                print("   ⚠️ No GraphQL accepted submissions found")
        except Exception as e:
            print(f"   ❌ GraphQL fetch failed: {e}")
        
        # Strategy 2: REST API with pagination
        print("📄 Fetching REST API submissions with pagination...")
        rest_submissions = []
        
        for page in range(10):  # Increased from 5 to 10 pages
            offset = page * 20
            try:
                batch = self.fetch_submission_history_rest(offset, 20)
                if batch:
                    rest_submissions.extend(batch)
                    if page == 0:
                        print(f"   ✓ REST API working, fetching more pages...")
                    time.sleep(0.3)  # Respectful delay
                else:
                    if page == 0:
                        print("   ⚠️ REST API returned no results")
                    break
            except Exception as e:
                print(f"   ❌ REST API page {page} failed: {e}")
                break
        
        if rest_submissions:
            print(f"   ✓ Found {len(rest_submissions)} submissions via REST API")
        
        # Smart merge all submissions
        if graphql_accepted or rest_submissions:
            merged_submissions = self.smart_merge_submissions(graphql_accepted, rest_submissions)
        else:
            merged_submissions = []
        
        # Sort by timestamp (newest first)
        merged_submissions.sort(key=lambda x: int(x.get('timestamp', 0)), reverse=True)
        
        print(f"\n🎉 Total unique submissions collected: {len(merged_submissions)}")
        return merged_submissions

    def get_comprehensive_profile(self, username: str) -> Optional[Dict]:
        """Get comprehensive user profile with enhanced statistics"""
        print(f"\n=== Fetching Comprehensive Profile for '{username}' ===")
        
        profile_query = {
            "query": """
            query getUserProfile($username: String!) {
                matchedUser(username: $username) {
                    username
                    profile {
                        realName
                        userAvatar
                        ranking
                        reputation
                        aboutMe
                        countryName
                        company
                        jobTitle
                        school
                        skillTags
                        postViewCount
                        solutionCount
                    }
                    submitStatsGlobal {
                        acSubmissionNum {
                            difficulty
                            count
                            submissions
                        }
                        totalSubmissionNum {
                            difficulty
                            count
                            submissions
                        }
                    }
                    badges {
                        id
                        displayName
                        icon
                        hoverText
                    }
                    userCalendar {
                        activeYears
                        streak
                        totalActiveDays
                        submissionCalendar
                    }
                }
            }
            """,
            "variables": {"username": username},
            "operationName": "getUserProfile"
        }
        
        try:
            response = self.session.post(
                'https://leetcode.com/graphql',
                json=profile_query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"❌ GraphQL errors: {data['errors']}")
                    return None
                
                user_data = data.get('data', {}).get('matchedUser')
                if user_data:
                    print("✅ Comprehensive profile fetched successfully!")
                    
                    # Display enhanced info
                    profile = user_data.get('profile', {})
                    print(f"   Real Name: {profile.get('realName', 'N/A')}")
                    print(f"   Global Ranking: #{profile.get('ranking', 'N/A'):,}" if profile.get('ranking') else "   Global Ranking: N/A")
                    print(f"   Country: {profile.get('countryName', 'N/A')}")
                    print(f"   Company: {profile.get('company', 'N/A')}")
                    print(f"   Solutions Posted: {profile.get('solutionCount', 0)}")
                    
                    # Display problem stats
                    stats = user_data.get('submitStatsGlobal', {})
                    ac_stats = stats.get('acSubmissionNum', [])
                    total_stats = stats.get('totalSubmissionNum', [])
                    
                    if ac_stats:
                        print("\n   📊 Problem Solving Statistics:")
                        for ac, total in zip(ac_stats, total_stats):
                            difficulty = ac.get('difficulty', 'Unknown')
                            solved = ac.get('count', 0)
                            total_attempts = total.get('count', 0)
                            acceptance = (solved / total_attempts * 100) if total_attempts > 0 else 0
                            print(f"     {difficulty}: {solved:,} solved / {total_attempts:,} attempted ({acceptance:.1f}%)")
                    
                    # Display calendar stats if available
                    calendar = user_data.get('userCalendar', {})
                    if calendar:
                        print(f"\n   📅 Activity Statistics:")
                        print(f"     Current Streak: {calendar.get('streak', 0)} days")
                        print(f"     Total Active Days: {calendar.get('totalActiveDays', 0)}")
                        print(f"     Active Years: {calendar.get('activeYears', [])}")
                    
                    # Fetch language statistics
                    lang_stats = self.fetch_language_statistics(username)
                    if lang_stats:
                        print(f"\n   🔤 Language Proficiency:")
                        for lang_stat in lang_stats[:5]:  # Show top 5
                            lang_name = lang_stat.get('languageName', 'Unknown')
                            problems_solved = lang_stat.get('problemsSolved', 0)
                            print(f"     {lang_name}: {problems_solved} problems")
                    
                    return user_data
                else:
                    print(f"❌ User '{username}' not found")
                    return None
            else:
                print(f"❌ Profile request failed. Status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Profile fetch error: {e}")
            return None

    def analyze_comprehensive_data(self, submissions: List[Dict], profile_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Comprehensive analysis with enhanced statistics"""
        print(f"\n=== Comprehensive Analysis of {len(submissions)} Submissions ===")
        
        if not submissions:
            print("❌ No submissions to analyze")
            return {}
        
        # Enhanced debugging
        if self.debug_mode:
            print("🔍 Detailed data structure analysis...")
            sample = submissions[0] if submissions else {}
            print(f"   Sample submission fields: {list(sample.keys())}")
        
        # Enhanced statistics
        total_submissions = len(submissions)
        accepted_submissions = []
        failed_submissions = []
        
        # Language and problem tracking
        language_stats = defaultdict(int)
        status_stats = defaultdict(int)
        problem_attempts = defaultdict(list)
        solved_problems = set()
        difficulty_stats = {'Easy': 0, 'Medium': 0, 'Hard': 0}
        
        # Time-based analysis
        yearly_stats = defaultdict(int)
        monthly_stats = defaultdict(int)
        
        # Process each submission
        for submission in submissions:
            # Normalize field names (handle both GraphQL and REST formats)
            title = submission.get('title') or submission.get('problem_title', 'Unknown')
            title_slug = submission.get('titleSlug') or submission.get('title_slug', '')
            lang = submission.get('lang') or submission.get('language', 'Unknown')
            
            # Enhanced status detection
            status = (submission.get('statusDisplay') or 
                     submission.get('status_display') or 
                     submission.get('status') or 
                     'Unknown')
            
            # Track attempts per problem
            if title_slug:
                problem_attempts[title_slug].append({
                    'status': status,
                    'lang': lang,
                    'timestamp': submission.get('timestamp')
                })
            
            # Acceptance detection
            is_accepted = (
                status == 'Accepted' or
                status == 10 or
                'Accepted' in str(status) or
                str(status).lower() == 'accepted'
            )
            
            if is_accepted:
                accepted_submissions.append(submission)
                if title_slug:
                    solved_problems.add(title_slug)
            else:
                failed_submissions.append(submission)
            
            # Language statistics
            language_stats[lang] += 1
            status_stats[status] += 1
            
            # Time-based analysis
            dt = self.fix_timestamp(submission.get('timestamp'))
            if dt:
                yearly_stats[dt.year] += 1
                month_key = f"{dt.year}-{dt.month:02d}"
                monthly_stats[month_key] += 1
        
        # Calculate advanced metrics
        acceptance_rate = (len(accepted_submissions) / total_submissions * 100) if total_submissions > 0 else 0
        unique_problems_attempted = len(problem_attempts)
        unique_problems_solved = len(solved_problems)
        
        # Problem solving efficiency
        problems_with_multiple_attempts = sum(1 for attempts in problem_attempts.values() if len(attempts) > 1)
        avg_attempts_per_problem = total_submissions / unique_problems_attempted if unique_problems_attempted > 0 else 0
        
        # Display comprehensive results
        print(f"📊 Overall Statistics:")
        print(f"   Total Submissions: {total_submissions:,}")
        print(f"   Accepted Submissions: {len(accepted_submissions):,}")
        print(f"   Failed Submissions: {len(failed_submissions):,}")
        print(f"   Overall Acceptance Rate: {acceptance_rate:.1f}%")
        print(f"   Unique Problems Attempted: {unique_problems_attempted:,}")
        print(f"   Unique Problems Solved: {unique_problems_solved:,}")
        print(f"   Problem Solving Rate: {(unique_problems_solved/unique_problems_attempted*100):.1f}%" if unique_problems_attempted > 0 else "   Problem Solving Rate: N/A")
        print(f"   Average Attempts per Problem: {avg_attempts_per_problem:.1f}")
        print(f"   Problems with Multiple Attempts: {problems_with_multiple_attempts}")
        
        print(f"\n🔤 Language Distribution:")
        sorted_languages = sorted(language_stats.items(), key=lambda x: x[1], reverse=True)
        for lang, count in sorted_languages:
            percentage = (count / total_submissions * 100)
            print(f"   {lang}: {count:,} submissions ({percentage:.1f}%)")
        
        print(f"\n📈 Status Distribution:")
        sorted_statuses = sorted(status_stats.items(), key=lambda x: x[1], reverse=True)
        for status, count in sorted_statuses[:10]:  # Show top 10 statuses
            percentage = (count / total_submissions * 100)
            emoji = "✅" if 'Accepted' in str(status) else "❌" if 'Wrong' in str(status) else "⚠️"
            print(f"   {emoji} {status}: {count:,} ({percentage:.1f}%)")
        
        print(f"\n📅 Year-wise Activity:")
        for year in sorted(yearly_stats.keys(), reverse=True):
            count = yearly_stats[year]
            print(f"   {year}: {count:,} submissions")
        
        # Recent activity with enhanced timestamp handling
        print(f"\n🕒 Recent Activity (Last 15 Submissions):")
        for i, submission in enumerate(submissions[:15], 1):
            title = submission.get('title') or submission.get('problem_title', 'Unknown')
            status = (submission.get('statusDisplay') or 
                     submission.get('status_display') or 
                     submission.get('status', 'Unknown'))
            lang = submission.get('lang') or submission.get('language', 'Unknown')
            
            dt = self.fix_timestamp(submission.get('timestamp'))
            time_str = dt.strftime('%Y-%m-%d %H:%M') if dt else 'Unknown time'
            
            is_accepted = 'Accepted' in str(status) or status == 10
            status_emoji = "✅" if is_accepted else "❌"
            source_emoji = "🔍" if submission.get('_source') == 'graphql' else "🌐"
            
            print(f"   {i:2d}. {status_emoji}{source_emoji} {title[:40]:<40} ({lang}) - {status} ({time_str})")
        
        return {
            'total_submissions': total_submissions,
            'accepted_submissions': len(accepted_submissions),
            'failed_submissions': len(failed_submissions),
            'acceptance_rate': acceptance_rate,
            'unique_problems_attempted': unique_problems_attempted,
            'unique_problems_solved': unique_problems_solved,
            'problem_solving_rate': (unique_problems_solved/unique_problems_attempted*100) if unique_problems_attempted > 0 else 0,
            'avg_attempts_per_problem': avg_attempts_per_problem,
            'problems_with_multiple_attempts': problems_with_multiple_attempts,
            'language_stats': dict(language_stats),
            'status_stats': dict(status_stats),
            'yearly_stats': dict(yearly_stats),
            'monthly_stats': dict(monthly_stats)
        }

    def save_enhanced_data(self, username: str, profile_data: Optional[Dict], 
                          submissions: List[Dict], analysis: Dict[str, Any]) -> None:
        """Save comprehensive data with multiple output formats"""
        
        timestamp = datetime.now()
        
        complete_data = {
            'metadata': {
                'username': username,
                'fetch_timestamp': timestamp.isoformat(),
                'total_submissions_fetched': len(submissions),
                'fetcher_version': '4.0_comprehensive',
                'data_sources': list(set(sub.get('_source', 'unknown') for sub in submissions))
            },
            'user_profile': profile_data,
            'submission_history': submissions,
            'comprehensive_analysis': analysis
        }
        
        # Save comprehensive JSON data
        json_filename = f'{username}_comprehensive_leetcode_data.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, indent=2, ensure_ascii=False)
        
        # Save enhanced summary report
        summary_filename = f'{username}_detailed_report.txt'
        with open(summary_filename, 'w', encoding='utf-8') as f:
            f.write(f"LeetCode Comprehensive Analysis Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Username: {username}\n")
            f.write(f"Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Fetcher Version: 4.0 Comprehensive\n\n")
            
            # Profile summary
            if profile_data:
                profile = profile_data.get('profile', {})
                f.write("PROFILE OVERVIEW\n")
                f.write("-" * 30 + "\n")
                f.write(f"Real Name: {profile.get('realName', 'N/A')}\n")
                f.write(f"Global Ranking: #{profile.get('ranking', 'N/A'):,}\n" if profile.get('ranking') else "Global Ranking: N/A\n")
                f.write(f"Country: {profile.get('countryName', 'N/A')}\n")
                f.write(f"Company: {profile.get('company', 'N/A')}\n\n")
            
            # Performance statistics
            f.write("PERFORMANCE STATISTICS\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total Submissions: {analysis.get('total_submissions', 0):,}\n")
            f.write(f"Accepted: {analysis.get('accepted_submissions', 0):,}\n")
            f.write(f"Failed: {analysis.get('failed_submissions', 0):,}\n")
            f.write(f"Acceptance Rate: {analysis.get('acceptance_rate', 0):.1f}%\n")
            f.write(f"Problems Attempted: {analysis.get('unique_problems_attempted', 0):,}\n")
            f.write(f"Problems Solved: {analysis.get('unique_problems_solved', 0):,}\n")
            f.write(f"Problem Solving Rate: {analysis.get('problem_solving_rate', 0):.1f}%\n")
            f.write(f"Avg Attempts per Problem: {analysis.get('avg_attempts_per_problem', 0):.1f}\n\n")
            
            # Language breakdown
            f.write("LANGUAGE PROFICIENCY\n")
            f.write("-" * 30 + "\n")
            for lang, count in sorted(analysis.get('language_stats', {}).items(), 
                                    key=lambda x: x[1], reverse=True):
                percentage = (count / analysis.get('total_submissions', 1) * 100)
                f.write(f"{lang}: {count:,} submissions ({percentage:.1f}%)\n")
            
            f.write("\n")
            
            # Year-wise activity
            f.write("YEARLY ACTIVITY\n")
            f.write("-" * 30 + "\n")
            for year in sorted(analysis.get('yearly_stats', {}).keys(), reverse=True):
                count = analysis['yearly_stats'][year]
                f.write(f"{year}: {count:,} submissions\n")
        
        # Save CSV for data analysis
        csv_filename = f'{username}_submissions_data.csv'
        try:
            import csv
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                if submissions:
                    fieldnames = ['title', 'titleSlug', 'lang', 'statusDisplay', 'timestamp', 'source', 'runtime', 'memory']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for sub in submissions:
                        dt = self.fix_timestamp(sub.get('timestamp'))
                        row = {
                            'title': sub.get('title', ''),
                            'titleSlug': sub.get('titleSlug', ''),
                            'lang': sub.get('lang', ''),
                            'statusDisplay': sub.get('statusDisplay', ''),
                            'timestamp': dt.isoformat() if dt else '',
                            'source': sub.get('_source', ''),
                            'runtime': sub.get('runtime', ''),
                            'memory': sub.get('memory', '')
                        }
                        writer.writerow(row)
        except ImportError:
            pass  # CSV module not available
        
        print(f"\n💾 Enhanced data saved:")
        print(f"   📄 Comprehensive JSON: {json_filename}")
        print(f"   📝 Detailed Report: {summary_filename}")
        if 'csv' in locals():
            print(f"   📊 CSV Data: {csv_filename}")


def run_comprehensive_leetcode_fetch():
    """Main function for comprehensive LeetCode data fetching"""
    print("🚀 LeetCode Comprehensive Data Fetcher v4.0")
    print("   Enhanced with smart merging, better timestamps, and comprehensive analysis\n")
    
    fetcher = LeetCodeSubmissionFetcher()
    
    # Ask for debug mode
    debug_choice = input("Enable debug mode? (y/N): ").strip().lower()
    fetcher.debug_mode = debug_choice == 'y'
    
    try:
        # Step 1: Authentication
        cookies = fetcher.extract_cookies_manual()
        session = fetcher.create_authenticated_session(cookies)
        
        if not fetcher.test_authentication():
            print("\n❌ Authentication failed. Please check your cookies and try again.")
            return
        
        # Step 2: Get username
        username = input("\nEnter your LeetCode username: ").strip()
        if not username:
            print("❌ Username is required!")
            return
        
        # Step 3: Comprehensive profile fetch
        print(f"\n🔄 Starting comprehensive data fetch for '{username}'...")
        profile_data = fetcher.get_comprehensive_profile(username)
        
        # Step 4: Comprehensive submission fetch
        print("⏳ This may take a few minutes for comprehensive data collection...")
        all_submissions = fetcher.fetch_comprehensive_data(username)
        
        if not all_submissions:
            print("❌ No submissions found using any method.")
            print("💡 Possible reasons:")
            print("   - No submissions in your account")
            print("   - Submissions are private")
            print("   - API changes or restrictions")
            return
        
        # Step 5: Comprehensive analysis
        analysis = fetcher.analyze_comprehensive_data(all_submissions, profile_data)
        
        # Step 6: Save enhanced data
        fetcher.save_enhanced_data(username, profile_data, all_submissions, analysis)
        
        print(f"\n🎉 Comprehensive analysis complete!")
        print(f"   📊 Analyzed {len(all_submissions):,} submissions")
        print(f"   🎯 Found {analysis.get('unique_problems_solved', 0)} unique problems solved")
        print(f"   📈 Overall acceptance rate: {analysis.get('acceptance_rate', 0):.1f}%")
        print("📁 Check the generated files for detailed insights.")
        
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user.")
        return
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if fetcher.debug_mode:
            import traceback
            traceback.print_exc()
        return


if __name__ == "__main__":
    run_comprehensive_leetcode_fetch()
