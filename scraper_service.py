import requests
import time
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain_community.chat_models import ChatOpenAI
import os
import json
import re

class ScraperService:
    
    @staticmethod
    def fetch_page_content(url, retry_count=3):
        """THE MINER: Fetches page via Jina to bypass WAF/JS. Handles rate limiting with retries."""
        jina_api_key = os.getenv("JINA_API_KEY")
        if jina_api_key:
            # With API key: use authenticated endpoint (200 req/min limit)
            jina_url = f"https://r.jina.ai/{url}"
            headers = {
                'Authorization': f'Bearer {jina_api_key}',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        else:
            # Without API key: free tier (20 req/min limit)
            jina_url = f"https://r.jina.ai/{url}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        
        for attempt in range(retry_count):
            try:
                response = requests.get(jina_url, headers=headers, timeout=25)
                
                if response.status_code == 200:
                    return response.text[:20000]  # Jina returns Markdown
                elif response.status_code == 429:
                    # Rate limited - wait with exponential backoff
                    wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                    if attempt < retry_count - 1:
                        print(f"Jina Rate Limit (429) - waiting {wait_time}s before retry {attempt + 1}/{retry_count}")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Jina Error: 429 Rate Limit exceeded after {retry_count} attempts")
                        return None
                else:
                    print(f"Jina Error: {response.status_code}")
                    return None
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = (2 ** attempt) * 1
                    print(f"Fetch Error (attempt {attempt + 1}/{retry_count}): {e} - retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Fetch Error: {e}")
                    return None
        
        return None

    @staticmethod
    def debug_fetch(url):
        """Diagnostics for the Settings Page."""
        log = {"steps": [], "preview": "", "success": False}
        jina_url = f"https://r.jina.ai/{url}"
        
        try:
            log["steps"].append(f"1. Routing via Jina Reader ({jina_url})...")
            start = time.time()
            response = requests.get(jina_url, timeout=25)
            duration = round(time.time() - start, 2)
            
            log["steps"].append(f"2. Response: {response.status_code} ({duration}s)")
            
            if response.status_code == 200:
                text = response.text
                log["steps"].append(f"3. Received {len(text)} chars of Markdown")
                log["preview"] = text[:1000] + "..."
                log["success"] = True
            else:
                log["steps"].append(f"3. Failed. Jina status: {response.status_code}")
                
        except Exception as e:
            log["steps"].append(f"ERROR: {str(e)}")
            
        return log

    @staticmethod
    def _extract_job_title_from_page(url):
        """Quickly extract job title from a job page."""
        try:
            content = ScraperService.fetch_page_content(url)
            if not content:
                return None
            
            # Use AI to extract just the job title (faster than full parsing)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            
            llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", openai_api_key=api_key)
            prompt = f"""
            Extract ONLY the job title from this job posting page content.
            Return just the job title as a plain string, nothing else.
            
            Content (first 2000 chars):
            {content[:2000]}
            
            Job title:"""
            
            result = llm.invoke(prompt)
            title = result.content.strip().strip('"').strip("'")
            # Clean up common AI prefixes
            title = re.sub(r'^(Job title:|Title:|The job title is:)\s*', '', title, flags=re.IGNORECASE)
            return title[:200]  # Limit length
        except Exception as e:
            print(f"DEBUG: Failed to extract title from {url[:50]}...: {e}")
            return None

    @staticmethod
    def discover_job_links(board_url, role_keyword):
        """THE SCOUT: Finds job links in Jina's Markdown output."""
        try:
            markdown_content = ScraperService.fetch_page_content(board_url)
            if not markdown_content:
                return []

            # Find [Title](URL) patterns
            link_pattern = r'\[([^\]]+)\]\((http[^\)]+)\)'
            matches = re.findall(link_pattern, markdown_content)
            
            candidates = []
            seen = set()
            for text, href in matches:
                if len(text) < 4 or "mailto" in href or "linkedin" in href:
                    continue
                # Only include job board URLs (greenhouse, lever, etc.) or links with "apply" text
                if ("greenhouse.io" in href.lower() or "lever.co" in href.lower() or 
                    "workday.com" in href.lower() or "apply" in text.lower()):
                    if href not in seen:
                        candidates.append({"text": text, "url": href})
                        seen.add(href)

            print(f"DEBUG: Filtering for keyword: '{role_keyword}'")
            print(f"DEBUG: Found {len(candidates)} candidate job links")
            
            if not candidates:
                return []
            
            # Fetch job titles for each candidate (check all, but limit results to top matches)
            matched_urls = []
            keyword_lower = role_keyword.lower()
            
            # Process all candidates, but stop early if we have enough matches
            max_matches = 20  # Stop after finding this many matches
            for i, candidate in enumerate(candidates):
                url = candidate['url']
                print(f"DEBUG: Checking job {i+1}/{len(candidates)}: {url[:60]}...")
                
                title = ScraperService._extract_job_title_from_page(url)
                if title:
                    title_lower = title.lower()
                    # Check if keyword matches title
                    if (keyword_lower in title_lower or 
                        (keyword_lower == "engineer" and "engineering" in title_lower) or
                        (keyword_lower == "analyst" and "analysis" in title_lower)):
                        matched_urls.append(url)
                        print(f"DEBUG: ✓ Matched: '{title}' ({len(matched_urls)}/{max_matches})")
                        
                        # Stop early if we have enough matches
                        if len(matched_urls) >= max_matches:
                            print(f"DEBUG: Found {max_matches} matches, stopping early")
                            break
                    else:
                        print(f"DEBUG: ✗ Skipped: '{title}' (doesn't match '{role_keyword}')")
                else:
                    print(f"DEBUG: ✗ Failed to extract title from {url[:60]}...")
                
                # Delay between requests to avoid rate limiting
                # Without API key: 20 req/min = 1 req per 3s, so wait 3.5s
                # With API key: 200 req/min = 1 req per 0.3s, so wait 0.5s
                jina_api_key = os.getenv("JINA_API_KEY")
                delay = 0.5 if jina_api_key else 3.5  # Faster with API key
                if i < len(candidates) - 1:
                    time.sleep(delay)
                    if not jina_api_key and i % 5 == 0:
                        print(f"DEBUG: Tip: Set JINA_API_KEY env var for 10x faster scraping (200 req/min vs 20 req/min)")
            
            print(f"DEBUG: Found {len(matched_urls)} matching jobs for '{role_keyword}'")
            return matched_urls  # Return all matched URLs (up to max_matches)
            
        except Exception as e:
            print(f"Discovery Error: {e}")
            return []
