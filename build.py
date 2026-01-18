import os
import requests
import markdown
from jinja2 import Environment, FileSystemLoader

ORG_NAME = "AccessMods"
GITHUB_TOKEN = os.environ.get('GH_TOKEN')
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def get_dynamic_nav():
    """
    Scans the content/ folder and builds the menu automatically.
    Always puts 'Home' (index) first.
    """
    nav_links = []
    
    # 1. Always add Home first
    nav_links.append({"title": "Home", "url": "index.html"})
    
    # 2. Find other MD files
    if os.path.exists('content'):
        for filename in os.listdir('content'):
            if filename == 'index.md': continue # Skip index, we handled it
            if filename.endswith('.md'):
                # Convert 'how-to-mod.md' -> 'How To Mod'
                title = filename.replace('.md', '').replace('-', ' ').title()
                url = filename.replace('.md', '.html')
                nav_links.append({"title": title, "url": url})
                
    return nav_links

def smart_asset_parser(repo_url, assets):
    """
    Analyzes release files.
    - Ignores Source Code.
    - Guesses OS based on name.
    - Fallback: Just lists the extension if unknown.
    """
    downloads = []
    
    for asset in assets:
        name = asset['name'].lower()
        url = asset['browser_download_url']
        
        # 1. Filter out Source Code zips (GitHub adds these automatically)
        if "source code" in name: continue
        
        # 2. Determine Label based on keywords
        label = "Download"
        if "win" in name or ".exe" in name:
            label = "Download for Windows"
        elif "mac" in name or "osx" in name or ".dmg" in name:
            label = "Download for Mac"
        elif "linux" in name or ".deb" in name or ".rpm" in name:
            label = "Download for Linux"
        
        # 3. Append extension (Useful if multiple zips exist, e.g., 'mod.zip' vs 'mod-debug.zip')
        ext = os.path.splitext(name)[1] 
        final_label = f"{label} ({ext})"
        
        downloads.append({"label": final_label, "url": url})
    
    # 4. SAFETY FALLBACK: If we found no binaries, or the list is empty, 
    # provide a link to the Repo Releases page so the user isn't stuck.
    if not downloads:
        downloads.append({"label": "View Release on GitHub", "url": f"{repo_url}/releases/latest"})
        
    return downloads

def get_org_data():
    print("Fetching data from GitHub...")
    try:
        url = f"https://api.github.com/orgs/{ORG_NAME}/repos?per_page=100"
        repos = requests.get(url, headers=HEADERS).json()
    except Exception as e:
        print(f"Error fetching repos: {e}")
        return "", ""
    
    mods_html = ""
    tools_html = ""

    # Sort repos alphabetically to be nice
    if isinstance(repos, list):
        repos.sort(key=lambda x: x['name'])

    for repo in repos:
        # Safety checks
        if not isinstance(repo, dict): continue
        if repo.get('archived') or repo.get('private'): continue
        
        topics = repo.get('topics', [])
        # Skip if it doesn't have our strict tags
        if "game-mod" not in topics and "dev-tool" not in topics: continue

        # Fetch Releases
        buttons_html = ""
        version_tag = ""
        
        try:
            rel_url = f"https://api.github.com/repos/{ORG_NAME}/{repo['name']}/releases/latest"
            rel_resp = requests.get(rel_url, headers=HEADERS)
            
            if rel_resp.status_code == 200:
                data = rel_resp.json()
                version_tag = f"<span class='version-tag'>{data['tag_name']}</span>"
                
                # Use the Smart Parser
                assets = smart_asset_parser(repo['html_url'], data.get('assets', []))
                
                for asset in assets:
                    buttons_html += f'<a href="{asset["url"]}" class="btn">{asset["label"]}</a> '
            else:
                # No releases found? Link to repo.
                version_tag = "<span class='version-tag'>In Development</span>"
                buttons_html = f'<a href="{repo["html_url"]}" class="btn secondary">View Source</a>'

        except Exception as e:
            print(f"Error processing {repo['name']}: {e}")
            buttons_html = f'<a href="{repo["html_url"]}" class="btn secondary">View on GitHub</a>'

        # Build the Card HTML
        repo_html = f"""
        <div class="card">
            <div class="card-header">
                <h3><a href="{repo['html_url']}">{repo['name']}</a> {version_tag}</h3>
                <div class="btn-group">{buttons_html}</div>
            </div>
            <p>{repo['description'] or 'No description provided.'}</p>
        </div>
        """
        
        if "game-mod" in topics:
            mods_html += repo_html
        elif "dev-tool" in topics:
            tools_html += repo_html
            
    # If empty, show a friendly message
    if not mods_html: mods_html = "<p>No mods found. Check back soon!</p>"
    if not tools_html: tools_html = "<p>No tools found.</p>"

    return f"""
    <h2 id="mods">Game Mods</h2>
    {mods_html}
    <h2 id="tools">Developer Tools</h2>
    {tools_html}
    """

def build():
    # Setup Jinja2
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('base.html')
    
    # Get Dynamic Navigation Links
    nav_links = get_dynamic_nav()
    
    # 1. Build Index (Home)
    repo_data = get_org_data()
    intro_text = ""
    if os.path.exists('content/index.md'):
        with open('content/index.md', 'r') as f:
            intro_text = markdown.markdown(f.read())
            
    with open('index.html', 'w', encoding="utf-8") as f:
        f.write(template.render(
            title="Home", 
            content=intro_text + repo_data,
            nav_links=nav_links
        ))
    print("Built index.html")

    # 2. Build Other Pages
    if os.path.exists('content'):
        for filename in os.listdir('content'):
            if filename == 'index.md': continue
            if filename.endswith('.md'):
                with open(f'content/{filename}', 'r') as f:
                    md_content = markdown.markdown(f.read())
                    page_name = filename.replace('.md', '').replace('-', ' ').title()
                    
                    output_filename = filename.replace('.md', '.html')
                    with open(output_filename, 'w', encoding="utf-8") as f:
                        f.write(template.render(
                            title=page_name,
                            content=md_content,
                            nav_links=nav_links
                        ))
                    print(f"Built {output_filename}")

if __name__ == "__main__":
    build()