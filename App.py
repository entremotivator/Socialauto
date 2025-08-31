import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from streamlit_calendar import calendar
import time
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="GetLate.dev API Dashboard",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e8b57;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .api-response {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .error-message {
        background-color: #ffe6e6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff4444;
        color: #cc0000;
    }
    .success-message {
        background-color: #e6ffe6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #44ff44;
        color: #006600;
    }
    .metric-container {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
    }
    .stSelectbox > div > div {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'profiles' not in st.session_state:
    st.session_state.profiles = []
if 'accounts' not in st.session_state:
    st.session_state.accounts = []
if 'posts_cache' not in st.session_state:
    st.session_state.posts_cache = {}
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# Helper functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def make_api_request(endpoint, method="GET", data=None, params=None, files=None, use_cache=True):
    """Make API request to GetLate.dev with caching and better error handling"""
    if not st.session_state.api_key:
        return None, "API key not provided"
    
    base_url = "https://getlate.dev/api/v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {st.session_state.api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == "POST":
            if files:
                # Remove Content-Type header for file uploads
                headers.pop("Content-Type", None)
                response = requests.post(url, headers=headers, files=files, timeout=60)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            return response.json(), None
        elif response.status_code == 401:
            return None, "Unauthorized: Please check your API key"
        elif response.status_code == 429:
            return None, "Rate limit exceeded. Please try again later"
        elif response.status_code == 500:
            return None, "Server error. Please try again later"
        else:
            try:
                error_detail = response.json().get('message', response.text)
            except:
                error_detail = response.text
            return None, f"Error {response.status_code}: {error_detail}"
    
    except requests.exceptions.Timeout:
        return None, "Request timed out. Please try again"
    except requests.exceptions.ConnectionError:
        return None, "Connection error. Please check your internet connection"
    except Exception as e:
        return None, f"Request failed: {str(e)}"

def load_profiles():
    """Load profiles from API with error handling"""
    with st.spinner("Loading profiles..."):
        data, error = make_api_request("/profiles")
        if data:
            st.session_state.profiles = data.get('profiles', [])
            return True, None
        return False, error

def load_accounts():
    """Load accounts from API with error handling"""
    with st.spinner("Loading accounts..."):
        data, error = make_api_request("/accounts")
        if data:
            st.session_state.accounts = data.get('accounts', [])
            return True, None
        return False, error

def validate_api_key():
    """Validate API key by making a test request"""
    if not st.session_state.api_key:
        return False, "No API key provided"
    
    data, error = make_api_request("/profiles")
    if data is not None:
        return True, "API key is valid"
    else:
        return False, error

def format_datetime(dt_string):
    """Format datetime string for display"""
    try:
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_string

def get_platform_icon(platform):
    """Get icon for platform"""
    icons = {
        'twitter': '🐦',
        'facebook': '📘',
        'instagram': '📸',
        'linkedin': '💼',
        'reddit': '🔴',
        'discord': '💬',
        'telegram': '✈️'
    }
    return icons.get(platform.lower(), '📱')

# Main app
def main():
    st.markdown('<div class="main-header">📱 GetLate.dev API Dashboard</div>', unsafe_allow_html=True)
    
    # Sidebar for API key and navigation
    with st.sidebar:
        st.header("🔑 API Configuration")
        
        # API Key input with validation
        api_key = st.text_input(
            "API Key", 
            value=st.session_state.api_key,
            type="password",
            help="Enter your GetLate.dev API key"
        )
        
        if api_key != st.session_state.api_key:
            st.session_state.api_key = api_key
            # Clear cache when API key changes
            st.cache_data.clear()
        
        # API Key validation
        if st.session_state.api_key:
            if st.button("🔍 Validate API Key"):
                is_valid, message = validate_api_key()
                if is_valid:
                    st.success(message)
                else:
                    st.error(message)
        
        # Data refresh with status
        if st.button("🔄 Refresh Data"):
            if st.session_state.api_key:
                with st.spinner("Refreshing..."):
                    profiles_success, profiles_error = load_profiles()
                    accounts_success, accounts_error = load_accounts()
                    
                    if profiles_success and accounts_success:
                        st.success("Data refreshed successfully!")
                        st.session_state.last_refresh = datetime.now()
                    else:
                        error_msg = profiles_error or accounts_error
                        st.error(f"Refresh failed: {error_msg}")
            else:
                st.error("Please enter your API key first")
        
        # Show last refresh time
        if st.session_state.last_refresh:
            st.caption(f"Last refreshed: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        st.markdown("---")
        st.header("📊 Navigation")
        page = st.selectbox(
            "Select Page",
            ["Dashboard", "Profiles", "Posts", "Calendar View", "Reddit Feed", "Reddit Search", "Usage Stats", "Analytics"]
        )
        
        # Quick stats in sidebar
        if st.session_state.profiles or st.session_state.accounts:
            st.markdown("---")
            st.header("📈 Quick Stats")
            st.metric("Profiles", len(st.session_state.profiles))
            st.metric("Accounts", len(st.session_state.accounts))
    
    # Main content area
    if not st.session_state.api_key:
        show_welcome_page()
        return
    
    # Page routing
    if page == "Dashboard":
        show_dashboard()
    elif page == "Profiles":
        show_profiles()
    elif page == "Posts":
        show_posts()
    elif page == "Calendar View":
        show_calendar_view()
    elif page == "Reddit Feed":
        show_reddit_feed()
    elif page == "Reddit Search":
        show_reddit_search()
    elif page == "Usage Stats":
        show_usage_stats()
    elif page == "Analytics":
        show_analytics()

def show_welcome_page():
    """Welcome page when no API key is provided"""
    st.markdown("### 🚀 Welcome to GetLate.dev Dashboard")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **GetLate.dev** is a powerful social media management platform that helps you:
        
        - 📅 Schedule posts across multiple platforms
        - 🔗 Connect multiple social media accounts
        - 📊 Track your posting analytics
        - 🔍 Search and browse Reddit content
        - 👥 Manage multiple profiles
        
        ### Getting Started
        1. 🔑 Get your API key from [GetLate.dev Dashboard](https://getlate.dev/dashboard)
        2. 📝 Enter it in the sidebar
        3. ✅ Click "Validate API Key" to test the connection
        4. 🔄 Click "Refresh Data" to load your profiles and accounts
        5. 🎉 Start managing your social media posts!
        """)
    
    with col2:
        st.info("💡 **Pro Tip:** Keep your API key secure and never share it with others!")
        
        # Feature highlights
        st.markdown("#### ✨ Dashboard Features")
        features = [
            "Real-time data refresh",
            "Interactive calendar view",
            "Reddit integration",
            "Usage analytics",
            "Multi-platform posting",
            "Profile management"
        ]
        for feature in features:
            st.markdown(f"• {feature}")

def show_dashboard():
    """Enhanced dashboard overview"""
    st.markdown('<div class="section-header">📊 Dashboard Overview</div>', unsafe_allow_html=True)
    
    # Load data if not already loaded
    if not st.session_state.profiles:
        profiles_success, profiles_error = load_profiles()
        if not profiles_success and profiles_error:
            st.error(f"Failed to load profiles: {profiles_error}")
    
    if not st.session_state.accounts:
        accounts_success, accounts_error = load_accounts()
        if not accounts_success and accounts_error:
            st.error(f"Failed to load accounts: {accounts_error}")
    
    # Enhanced metrics with better visuals
    usage_data, usage_error = make_api_request("/usage-stats")
    posts_data, posts_error = make_api_request("/posts")
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            "👤 Profiles", 
            len(st.session_state.profiles),
            help="Number of profiles in your account"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        connected_accounts = len(st.session_state.accounts)
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            "🔗 Connected Accounts", 
            connected_accounts,
            help="Number of connected social media accounts"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        if posts_data and posts_data.get('posts'):
            total_posts = len(posts_data['posts'])
            scheduled_posts = len([p for p in posts_data['posts'] if p.get('scheduledFor')])
            st.metric(
                "📝 Total Posts",
                total_posts,
                delta=f"{scheduled_posts} scheduled",
                help="Total posts with scheduled count"
            )
        else:
            st.metric("📝 Total Posts", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        if usage_data:
            uploads = usage_data.get('uploads', {})
            current = uploads.get('current', 0)
            limit = uploads.get('limit', 'N/A')
            st.metric(
                "📤 Uploads Used", 
                f"{current}/{limit}",
                help="Monthly upload usage"
            )
        else:
            st.metric("📤 Uploads Used", "N/A")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Account breakdown
    if st.session_state.accounts:
        st.markdown('<div class="section-header">🔗 Connected Platforms</div>', unsafe_allow_html=True)
        
        platform_counts = {}
        for account in st.session_state.accounts:
            platform = account.get('platform', 'Unknown')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        cols = st.columns(min(len(platform_counts), 5))
        for i, (platform, count) in enumerate(platform_counts.items()):
            with cols[i % 5]:
                st.metric(
                    f"{get_platform_icon(platform)} {platform.title()}",
                    count,
                    help=f"Connected {platform} accounts"
                )
    
    # Recent activity with enhanced display
    st.markdown('<div class="section-header">📈 Recent Activity</div>', unsafe_allow_html=True)
    
    if posts_data and posts_data.get('posts'):
        posts_df = pd.DataFrame(posts_data['posts'])
        
        if not posts_df.empty:
            # Convert datetime and sort
            posts_df['createdAt'] = pd.to_datetime(posts_df['createdAt'], errors='coerce')
            posts_df = posts_df.sort_values('createdAt', ascending=False).head(10)
            
            # Enhanced posts display
            for _, post in posts_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([6, 2, 2])
                    
                    with col1:
                        # Post content with truncation
                        content = post['content']
                        if len(content) > 100:
                            content = content[:100] + "..."
                        st.markdown(f"**{content}**")
                        
                        # Platform badges
                        platforms = post.get('platforms', [])
                        if platforms:
                            platform_badges = []
                            for p in platforms:
                                platform_name = p.get('platform', 'Unknown')
                                icon = get_platform_icon(platform_name)
                                platform_badges.append(f"{icon} {platform_name.title()}")
                            st.markdown(f"*Platforms:* {' • '.join(platform_badges)}")
                    
                    with col2:
                        if pd.notna(post['createdAt']):
                            st.markdown(f"**Created:**  \n{post['createdAt'].strftime('%Y-%m-%d %H:%M')}")
                        
                        scheduled_for = post.get('scheduledFor')
                        if scheduled_for:
                            st.markdown(f"**Scheduled:**  \n{format_datetime(scheduled_for)}")
                    
                    with col3:
                        # Status indicators
                        if platforms:
                            status = platforms[0].get('status', 'unknown')
                            if status == 'scheduled':
                                st.success("⏰ Scheduled")
                            elif status == 'published':
                                st.success("✅ Published")
                            elif status == 'failed':
                                st.error("❌ Failed")
                            else:
                                st.info(f"📋 {status.title()}")
                    
                    st.markdown("---")
        else:
            st.info("📝 No posts found. Create your first post in the Posts section!")
    else:
        if posts_error:
            st.error(f"Failed to load posts: {posts_error}")
        else:
            st.info("📝 No posts found. Create your first post in the Posts section!")

def show_profiles():
    """Enhanced profiles management"""
    st.markdown('<div class="section-header">👤 Profiles Management</div>', unsafe_allow_html=True)
    
    # Load profiles with error handling
    if not st.session_state.profiles:
        success, error = load_profiles()
        if not success and error:
            st.error(f"Failed to load profiles: {error}")
            return
    
    # Create new profile with validation
    with st.expander("➕ Create New Profile", expanded=False):
        with st.form("create_profile", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                name = st.text_input("Profile Name*", placeholder="e.g., Personal, Business, Brand")
                description = st.text_area("Description", placeholder="Brief description of this profile")
            
            with col2:
                color = st.color_picker("Profile Color", "#1f77b4")
                st.markdown("**Preview:**")
                st.markdown(f'<div style="width: 50px; height: 50px; background-color: {color}; border-radius: 50%; margin: 10px 0;"></div>', unsafe_allow_html=True)
            
            col3, col4 = st.columns(2)
            with col3:
                set_default = st.checkbox("Set as default profile")
            
            with col4:
                submitted = st.form_submit_button("Create Profile", type="primary")
            
            if submitted:
                if not name.strip():
                    st.error("Profile name is required")
                elif len(name.strip()) < 2:
                    st.error("Profile name must be at least 2 characters")
                else:
                    data = {
                        "name": name.strip(),
                        "description": description.strip(),
                        "color": color,
                        "isDefault": set_default
                    }
                    
                    with st.spinner("Creating profile..."):
                        result, error = make_api_request("/profiles", "POST", data)
                        if result:
                            st.success(f"✅ Profile '{name}' created successfully!")
                            load_profiles()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to create profile: {error}")
    
    # Enhanced profiles display
    if st.session_state.profiles:
        st.markdown("### 📋 Your Profiles")
        
        # Search and filter
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("🔍 Search profiles", placeholder="Search by name or description")
        with col2:
            show_default_only = st.checkbox("Show default only")
        
        # Filter profiles
        filtered_profiles = st.session_state.profiles
        if search_term:
            filtered_profiles = [
                p for p in filtered_profiles 
                if search_term.lower() in p.get('name', '').lower() 
                or search_term.lower() in p.get('description', '').lower()
            ]
        
        if show_default_only:
            filtered_profiles = [p for p in filtered_profiles if p.get('isDefault')]
        
        # Display profiles in cards
        for i, profile in enumerate(filtered_profiles):
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 4, 2, 1])
                
                with col1:
                    # Color indicator
                    color = profile.get('color', '#cccccc')
                    st.markdown(f'<div style="width: 40px; height: 40px; background-color: {color}; border-radius: 50%; margin: 10px 0;"></div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"**{profile['name']}**")
                    if profile.get('description'):
                        st.markdown(f"*{profile['description']}*")
                    
                    # Profile metadata
                    created_at = profile.get('createdAt')
                    if created_at:
                        st.caption(f"Created: {format_datetime(created_at)}")
                
                with col3:
                    if profile.get('isDefault'):
                        st.success("🌟 Default Profile")
                    
                    # Profile ID for advanced users
                    with st.expander("🔧 Advanced"):
                        st.code(f"ID: {profile.get('_id', 'N/A')}")
                
                with col4:
                    # Action buttons
                    if st.button("✏️", key=f"edit_{i}", help="Edit profile"):
                        st.info("Edit functionality coming soon!")
                    
                    if st.button("🗑️", key=f"delete_{i}", help="Delete profile"):
                        if not profile.get('isDefault'):
                            st.error("Delete functionality coming soon!")
                        else:
                            st.warning("Cannot delete default profile")
                
                st.markdown("---")
    else:
        st.info("🎯 No profiles found. Create your first profile above to get started!")

def show_posts():
    """Enhanced posts management"""
    st.markdown('<div class="section-header">📝 Posts Management</div>', unsafe_allow_html=True)
    
    # Load accounts
    if not st.session_state.accounts:
        success, error = load_accounts()
        if not success and error:
            st.error(f"Failed to load accounts: {error}")
            return
    
    # Enhanced post creation
    with st.expander("➕ Schedule New Post", expanded=True):
        with st.form("create_post", clear_on_submit=False):
            # Media upload section
            st.markdown("#### 📷 Media Upload")
            uploaded_file = st.file_uploader(
                "Upload Image", 
                type=["png", "jpg", "jpeg", "gif", "webp"],
                help="Supported formats: PNG, JPG, JPEG, GIF, WebP"
            )
            
            media_url = None
            if uploaded_file is not None:
                # Show image preview
                st.image(uploaded_file, caption="Preview", width=200)
                
                if st.form_submit_button("📤 Upload Image", type="secondary"):
                    with st.spinner("Uploading image..."):
                        files = {"files": uploaded_file.getvalue()}
                        media_response, media_error = make_api_request("/media", "POST", files=files)
                        if media_response and media_response.get("files"):
                            media_url = media_response["files"][0]["url"]
                            st.success(f"✅ Image uploaded successfully!")
                            st.markdown(f"**URL:** {media_url}")
                        else:
                            st.error(f"❌ Failed to upload image: {media_error}")
            
            st.markdown("#### ✍️ Post Content")
            content = st.text_area(
                "Post Content*", 
                height=150,
                placeholder="What's on your mind? Write your post content here...",
                help="The main content of your post"
            )
            
            # Character counter
            if content:
                char_count = len(content)
                if char_count > 280:  # Twitter limit example
                    st.warning(f"⚠️ Content is {char_count} characters (Twitter limit: 280)")
                else:
                    st.info(f"📝 {char_count} characters")
            
            # Scheduling section
            st.markdown("#### ⏰ Scheduling")
            col1, col2 = st.columns(2)
            
            with col1:
                schedule_option = st.radio(
                    "When to post:",
                    ["Schedule for later", "Post immediately"],
                    help="Choose when to publish your post"
                )
                
                if schedule_option == "Schedule for later":
                    scheduled_date = st.date_input(
                        "Scheduled Date", 
                        min_value=datetime.now().date(),
                        value=datetime.now().date()
                    )
                    scheduled_time = st.time_input(
                        "Scheduled Time", 
                        value=(datetime.now() + timedelta(hours=1)).time()
                    )
                else:
                    scheduled_date = None
                    scheduled_time = None
            
            with col2:
                timezone = st.selectbox(
                    "Timezone",
                    [
                        "America/New_York", "America/Los_Angeles", "America/Chicago",
                        "Europe/London", "Europe/Paris", "Europe/Berlin",
                        "Asia/Tokyo", "Asia/Shanghai", "Australia/Sydney"
                    ],
                    index=0,
                    help="Select your timezone for scheduling"
                )
            
            # Platform selection with enhanced UI
            st.markdown("#### 🌐 Platform Selection")
            
            if not st.session_state.accounts:
                st.warning("⚠️ No connected accounts found. Please connect accounts first.")
                st.stop()
            
            selected_accounts = []
            
            # Group accounts by platform
            platform_groups = {}
            for account in st.session_state.accounts:
                platform = account['platform']
                if platform not in platform_groups:
                    platform_groups[platform] = []
                platform_groups[platform].append(account)
            
            # Display by platform
            for platform, accounts in platform_groups.items():
                st.markdown(f"**{get_platform_icon(platform)} {platform.title()}**")
                
                for account in accounts:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        account_selected = st.checkbox(
                            f"@{account['username']}", 
                            key=f"account_{account['_id']}"
                        )
                    
                    with col2:
                        if account.get('isActive', True):
                            st.success("🟢 Active")
                        else:
                            st.error("🔴 Inactive")
                    
                    if account_selected:
                        platform_data = {
                            "platform": account['platform'],
                            "accountId": account['_id']
                        }
                        
                        # Platform-specific options
                        if account['platform'] == 'reddit':
                            with st.container():
                                subcol1, subcol2 = st.columns(2)
                                with subcol1:
                                    subreddit = st.text_input(
                                        f"Subreddit*", 
                                        key=f"subreddit_{account['_id']}",
                                        placeholder="e.g., programming"
                                    )
                                with subcol2:
                                    post_type = st.selectbox(
                                        "Post Type",
                                        ["text", "link", "image"],
                                        key=f"type_{account['_id']}"
                                    )
                                
                                if post_type == "link":
                                    url = st.text_input(
                                        "URL*", 
                                        key=f"url_{account['_id']}",
                                        placeholder="https://example.com"
                                    )
                                else:
                                    url = None
                                
                                if subreddit:
                                    platform_data["platformSpecificData"] = {
                                        "subreddit": subreddit,
                                        "type": post_type
                                    }
                                    if url:
                                        platform_data["platformSpecificData"]["url"] = url
                        
                        selected_accounts.append(platform_data)
            
            # Form submission
            col1, col2 = st.columns([3, 1])
            
            with col1:
                submitted = st.form_submit_button("📅 Schedule Post", type="primary")
            
            with col2:
                draft_saved = st.form_submit_button("💾 Save Draft")
            
            if submitted:
                # Validation
                errors = []
                if not content.strip():
                    errors.append("Post content is required")
                if not selected_accounts:
                    errors.append("At least one platform must be selected")
                
                # Reddit-specific validation
                for acc_data in selected_accounts:
                    if acc_data['platform'] == 'reddit':
                        reddit_data = acc_data.get('platformSpecificData', {})
                        if not reddit_data.get('subreddit'):
                            errors.append("Subreddit is required for Reddit posts")
                        if reddit_data.get('type') == 'link' and not reddit_data.get('url'):
                            errors.append("URL is required for Reddit link posts")
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    # Prepare data
                    data = {
                        "content": content.strip(),
                        "platforms": selected_accounts
                    }
                    
                    if schedule_option == "Schedule for later" and scheduled_date and scheduled_time:
                        scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
                        data["scheduledFor"] = scheduled_datetime.isoformat()
                        data["timezone"] = timezone
                    
                    if media_url:
                        data["mediaItems"] = [{
                            "type": "image",
                            "url": media_url
                        }]
                    
                    # Submit post
                    with st.spinner("Scheduling post..."):
                        result, error = make_api_request("/posts", "POST", data)
                        if result:
                            st.success("✅ Post scheduled successfully!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to schedule post: {error}")
            
            elif draft_saved:
                st.info("💾 Draft save functionality coming soon!")
    
    # Enhanced posts display
    st.markdown("### 📋 Your Posts")
    
    # Filters and sorting
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Scheduled", "Published", "Failed", "Draft"]
        )
    
    with col2:
        platform_filter = st.selectbox(
            "Filter by Platform",
            ["All"] + list(set([acc['platform'].title() for acc in st.session_state.accounts]))
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Created Date (Newest)", "Created Date (Oldest)", "Scheduled Date", "Content Length"]
        )
    
    # Load and display posts
    posts_data, error = make_api_request("/posts")
    
    if posts_data and posts_data.get('posts'):
        posts = posts_data['posts']
        
        # Apply filters
        if status_filter != "All":
            posts = [p for p in posts if any(
                plat.get('status', '').lower() == status_filter.lower() 
                for plat in p.get('platforms', [])
            )]
        
        if platform_filter != "All":
            posts = [p for p in posts if any(
                plat.get('platform', '').title() == platform_filter 
                for plat in p.get('platforms', [])
            )]
        
        # Sort posts
        if sort_by == "Created Date (Newest)":
            posts.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        elif sort_by == "Created Date (Oldest)":
            posts.sort(key=lambda x: x.get('createdAt', ''))
        elif sort_by == "Scheduled Date":
            posts.sort(key=lambda x: x.get('scheduledFor', ''))
        elif sort_by == "Content Length":
            posts.sort(key=lambda x: len(x.get('content', '')), reverse=True)
        
        st.markdown(f"**Found {len(posts)} posts**")
        
        # Pagination
        posts_per_page = 10
        total_pages = (len(posts) + posts_per_page - 1) // posts_per_page
        
        if total_pages > 1:
            page_num = st.selectbox("Page", range(1, total_pages + 1))
            start_idx = (page_num - 1) * posts_per_page
            end_idx = start_idx + posts_per_page
            posts = posts[start_idx:end_idx]
        
        # Display posts
        for i, post in enumerate(posts):
            with st.container():
                # Post header
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.markdown(f"### 📄 Post #{i+1}")
                
                with col2:
                    # Action menu
                    with st.popover("⚙️ Actions"):
                        if st.button("✏️ Edit", key=f"edit_post_{i}"):
                            st.info("Edit functionality coming soon!")
                        if st.button("📋 Duplicate", key=f"dup_post_{i}"):
                            st.info("Duplicate functionality coming soon!")
                        if st.button("🗑️ Delete", key=f"del_post_{i}"):
                            st.info("Delete functionality coming soon!")
                
                # Post content
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown("**Content:**")
                    st.markdown(f'<div class="api-response">{post["content"]}</div>', unsafe_allow_html=True)
                    
                    # Media items
                    media_items = post.get('mediaItems', [])
                    if media_items:
                        st.markdown("**Media:**")
                        for media in media_items:
                            if media.get('type') == 'image':
                                try:
                                    st.image(media['url'], width=200)
                                except:
                                    st.markdown(f"🖼️ [Image]({media['url']})")
                
                with col2:
                    # Post metadata
                    st.markdown("**Details:**")
                    
                    created_at = post.get('createdAt')
                    if created_at:
                        st.markdown(f"**Created:** {format_datetime(created_at)}")
                    
                    scheduled_for = post.get('scheduledFor')
                    if scheduled_for:
                        st.markdown(f"**Scheduled:** {format_datetime(scheduled_for)}")
                    
                    timezone = post.get('timezone')
                    if timezone:
                        st.markdown(f"**Timezone:** {timezone}")
                
                # Platform status
                st.markdown("**Platform Status:**")
                platforms = post.get('platforms', [])
                
                if platforms:
                    for platform in platforms:
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            platform_name = platform.get('platform', 'Unknown')
                            st.markdown(f"{get_platform_icon(platform_name)} **{platform_name.title()}**")
                        
                        with col2:
                            status = platform.get('status', 'unknown')
                            if status == 'scheduled':
                                st.success("⏰ Scheduled")
                            elif status == 'published':
                                st.success("✅ Published")
                            elif status == 'failed':
                                st.error("❌ Failed")
                            else:
                                st.info(f"📋 {status.title()}")
                        
                        with col3:
                            # Platform-specific data
                            platform_data = platform.get('platformSpecificData', {})
                            if platform_data:
                                with st.popover("ℹ️ Details"):
                                    st.json(platform_data)
                
                st.markdown("---")
    
    else:
        if error:
            st.error(f"Failed to load posts: {error}")
        else:
            st.info("📝 No posts found. Schedule your first post above!")

def show_calendar_view():
    """Enhanced calendar view with better event handling"""
    st.markdown('<div class="section-header">🗓️ Scheduled Posts Calendar</div>', unsafe_allow_html=True)
    
    # Calendar controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        view_type = st.selectbox(
            "Calendar View",
            ["Month", "Week", "Day"],
            help="Choose your preferred calendar view"
        )
    
    with col2:
        show_all_posts = st.checkbox("Show all posts", value=False, help="Include past posts")
    
    with col3:
        if st.button("🔄 Refresh Calendar"):
            st.cache_data.clear()
            st.rerun()
    
    posts_data, error = make_api_request("/posts")

    if posts_data and posts_data.get("posts"):
        events = []
        color_map = {
            'scheduled': '#3498db',  # Blue
            'published': '#2ecc71',  # Green
            'failed': '#e74c3c',     # Red
            'draft': '#f39c12'       # Orange
        }
        
        for post in posts_data["posts"]:
            scheduled_for = post.get("scheduledFor")
            created_at = post.get("createdAt")
            
            # Determine which date to use
            event_date = scheduled_for or created_at
            
            if event_date:
                try:
                    # Handle different datetime formats
                    if event_date.endswith('Z'):
                        start_time = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                    else:
                        start_time = datetime.fromisoformat(event_date)
                    
                    # Filter past posts if needed
                    if not show_all_posts and start_time < datetime.now():
                        continue
                    
                    platforms = ", ".join([f"{get_platform_icon(p['platform'])} {p['platform'].title()}" 
                                         for p in post.get("platforms", [])])
                    
                    # Determine event color based on status
                    status = 'draft'
                    if post.get('platforms'):
                        status = post['platforms'][0].get('status', 'draft')
                    
                    # Truncate content for title
                    content_preview = post['content'][:40] + "..." if len(post['content']) > 40 else post['content']
                    
                    event = {
                        "title": f"{content_preview}",
                        "start": start_time.isoformat(),
                        "end": (start_time + timedelta(hours=1)).isoformat(),
                        "id": post["_id"],
                        "color": color_map.get(status, '#95a5a6'),
                        "extendedProps": {
                            "platforms": platforms,
                            "status": status,
                            "fullContent": post['content']
                        }
                    }
                    events.append(event)
                    
                except ValueError as e:
                    st.warning(f"Could not parse datetime: {event_date} - {e}")
                    continue

        if events:
            # Calendar options
            view_mapping = {
                "Month": "dayGridMonth",
                "Week": "timeGridWeek", 
                "Day": "timeGridDay"
            }
            
            calendar_options = {
                "headerToolbar": {
                    "left": "today prev,next",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,timeGridDay"
                },
                "initialView": view_mapping[view_type],
                "editable": False,
                "selectable": True,
                "selectMirror": True,
                "dayMaxEvents": True,
                "weekends": True,
                "initialDate": datetime.now().isoformat(),
                "height": 600,
                "eventDisplay": "block",
                "displayEventTime": True
            }

            # Render calendar
            state = calendar(events=events, options=calendar_options, key="posts_calendar")
            
            # Event details section
            st.markdown("### 📋 Event Details")
            
            if state and state.get("eventClick"):
                clicked_event = state["eventClick"]["event"]
                clicked_post = next((p for p in posts_data["posts"] if p["_id"] == clicked_event["id"]), None)
                
                if clicked_post:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("#### 📄 Post Content")
                        st.markdown(f'<div class="api-response">{clicked_post["content"]}</div>', unsafe_allow_html=True)
                        
                        # Media display
                        media_items = clicked_post.get('mediaItems', [])
                        if media_items:
                            st.markdown("#### 🖼️ Media")
                            for media in media_items:
                                if media.get('type') == 'image':
                                    st.image(media['url'], width=300)
                    
                    with col2:
                        st.markdown("#### ℹ️ Details")
                        
                        # Post metadata
                        st.markdown(f"**ID:** `{clicked_post['_id']}`")
                        
                        created_at = clicked_post.get('createdAt')
                        if created_at:
                            st.markdown(f"**Created:** {format_datetime(created_at)}")
                        
                        scheduled_for = clicked_post.get('scheduledFor')
                        if scheduled_for:
                            st.markdown(f"**Scheduled:** {format_datetime(scheduled_for)}")
                        
                        timezone = clicked_post.get('timezone')
                        if timezone:
                            st.markdown(f"**Timezone:** {timezone}")
                        
                        # Platform details
                        st.markdown("#### 🌐 Platforms")
                        for platform in clicked_post.get('platforms', []):
                            platform_name = platform.get('platform', 'Unknown')
                            status = platform.get('status', 'unknown')
                            
                            if status == 'scheduled':
                                st.success(f"{get_platform_icon(platform_name)} {platform_name.title()}: Scheduled")
                            elif status == 'published':
                                st.success(f"{get_platform_icon(platform_name)} {platform_name.title()}: Published")
                            elif status == 'failed':
                                st.error(f"{get_platform_icon(platform_name)} {platform_name.title()}: Failed")
                            else:
                                st.info(f"{get_platform_icon(platform_name)} {platform_name.title()}: {status.title()}")
                            
                            # Platform-specific data
                            platform_data = platform.get('platformSpecificData', {})
                            if platform_data:
                                with st.expander(f"📋 {platform_name.title()} Details"):
                                    st.json(platform_data)
                
                else:
                    st.error("Post details not found")
            else:
                st.info("👆 Click on a calendar event to see its details")
                
                # Legend
                st.markdown("#### 🎨 Status Legend")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown('<div style="display: flex; align-items: center;"><div style="width: 20px; height: 20px; background-color: #3498db; border-radius: 3px; margin-right: 8px;"></div>Scheduled</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div style="display: flex; align-items: center;"><div style="width: 20px; height: 20px; background-color: #2ecc71; border-radius: 3px; margin-right: 8px;"></div>Published</div>', unsafe_allow_html=True)
                
                with col3:
                    st.markdown('<div style="display: flex; align-items: center;"><div style="width: 20px; height: 20px; background-color: #e74c3c; border-radius: 3px; margin-right: 8px;"></div>Failed</div>', unsafe_allow_html=True)
                
                with col4:
                    st.markdown('<div style="display: flex; align-items: center;"><div style="width: 20px; height: 20px; background-color: #f39c12; border-radius: 3px; margin-right: 8px;"></div>Draft</div>', unsafe_allow_html=True)
        
        else:
            st.info("📅 No posts to display in calendar. Schedule your first post!")
    
    else:
        if error:
            st.error(f"Failed to load posts: {error}")
        else:
            st.info("📅 No posts found for calendar view.")

def show_reddit_feed():
    """Enhanced Reddit feed viewer"""
    st.markdown('<div class="section-header">🔴 Reddit Feed</div>', unsafe_allow_html=True)
    
    # Load accounts
    if not st.session_state.accounts:
        success, error = load_accounts()
        if not success and error:
            st.error(f"Failed to load accounts: {error}")
            return
    
    reddit_accounts = [acc for acc in st.session_state.accounts if acc['platform'] == 'reddit']
    
    if not reddit_accounts:
        st.warning("⚠️ No Reddit accounts connected. Please connect a Reddit account first.")
        return
    
    # Enhanced feed controls
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            selected_account = st.selectbox(
                "🔴 Reddit Account",
                reddit_accounts,
                format_func=lambda x: f"u/{x['username']}"
            )
        
        with col2:
            subreddit = st.text_input(
                "📂 Subreddit", 
                placeholder="e.g., programming, reactjs",
                help="Leave empty for home feed"
            )
        
        with col3:
            sort_option = st.selectbox("📊 Sort", ["hot", "new", "top", "rising"])
        
        with col4:
            limit = st.slider("📏 Limit", 1, 100, 25)
    
    # Time filter for 'top' sort
    if sort_option == "top":
        time_filter = st.selectbox(
            "⏰ Time Filter", 
            ["hour", "day", "week", "month", "year", "all"],
            index=2  # Default to week
        )
    else:
        time_filter = None
    
    # Load feed button
    if st.button("🔄 Load Feed", type="primary"):
        params = {
            "accountId": selected_account['_id'],
            "sort": sort_option,
            "limit": limit
        }
        
        if subreddit.strip():
            params["subreddit"] = subreddit.strip()
        
        if time_filter:
            params["t"] = time_filter
        
        with st.spinner(f"Loading {sort_option} posts..."):
            feed_data, error = make_api_request("/reddit/feed", params=params)
        
        if feed_data:
            items = feed_data.get('items', [])
            st.success(f"✅ Loaded {len(items)} posts")
            
            # Feed statistics
            if items:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    avg_score = sum(item.get('score', 0) for item in items) / len(items)
                    st.metric("📊 Avg Score", f"{avg_score:.1f}")
                
                with col2:
                    total_comments = sum(item.get('numComments', 0) for item in items)
                    st.metric("💬 Total Comments", total_comments)
                
                with col3:
                    unique_authors = len(set(item.get('author', '') for item in items))
                    st.metric("👥 Unique Authors", unique_authors)
            
            # Enhanced post display
            for i, item in enumerate(items):
                with st.container():
                    # Post header
                    col1, col2 = st.columns([5, 1])
                    
                    with col1:
                        st.markdown(f"### 📄 {item.get('title', 'Untitled')}")
                    
                    with col2:
                        # Quick actions
                        with st.popover("⚙️"):
                            if st.button("📋 Copy Title", key=f"copy_title_{i}"):
                                st.code(item.get('title', ''))
                            if st.button("🔗 Copy URL", key=f"copy_url_{i}"):
                                reddit_url = f"https://reddit.com{item.get('permalink', '')}"
                                st.code(reddit_url)
                    
                    # Post metadata
                    col1, col2, col3 = st.columns([4, 1, 1])
                    
                    with col1:
                        # Author and subreddit
                        author = item.get('author', 'Unknown')
                        subreddit_name = item.get('subreddit', 'Unknown')
                        st.markdown(f"👤 **u/{author}** in **r/{subreddit_name}**")
                        
                        # Post content
                        selftext = item.get('selftext', '')
                        if selftext:
                            if len(selftext) > 300:
                                with st.expander("📖 Read full text"):
                                    st.markdown(selftext)
                                st.markdown(f"{selftext[:300]}...")
                            else:
                                st.markdown(selftext)
                        
                        # External URL
                        url = item.get('url', '')
                        if url and not url.startswith('https://www.reddit.com'):
                            st.markdown(f"🔗 [External Link]({url})")
                        
                        # Reddit link
                        permalink = item.get('permalink', '')
                        if permalink:
                            reddit_url = f"https://reddit.com{permalink}"
                            st.markdown(f"💬 [View on Reddit]({reddit_url})")
                    
                    with col2:
                        # Engagement metrics
                        score = item.get('score', 0)
                        if score > 1000:
                            st.metric("🔥 Score", f"{score/1000:.1f}k")
                        else:
                            st.metric("👍 Score", score)
                        
                        num_comments = item.get('numComments', 0)
                        st.metric("💬 Comments", num_comments)
                    
                    with col3:
                        # Post metadata
                        created_utc = item.get('createdUtc')
                        if created_utc:
                            created_dt = datetime.fromtimestamp(created_utc)
                            time_ago = datetime.now() - created_dt
                            
                            if time_ago.days > 0:
                                st.markdown(f"📅 {time_ago.days}d ago")
                            elif time_ago.seconds > 3600:
                                st.markdown(f"⏰ {time_ago.seconds//3600}h ago")
                            else:
                                st.markdown(f"⏰ {time_ago.seconds//60}m ago")
                        
                        # Post flair
                        flair = item.get('linkFlairText')
                        if flair:
                            st.markdown(f"🏷️ {flair}")
                    
                    st.markdown("---")
        else:
            st.error(f"❌ Failed to load feed: {error}")

def show_reddit_search():
    """Enhanced Reddit search with filters"""
    st.markdown('<div class="section-header">🔍 Reddit Search</div>', unsafe_allow_html=True)
    
    # Load accounts
    if not st.session_state.accounts:
        success, error = load_accounts()
        if not success and error:
            st.error(f"Failed to load accounts: {error}")
            return
    
    reddit_accounts = [acc for acc in st.session_state.accounts if acc['platform'] == 'reddit']
    
    if not reddit_accounts:
        st.warning("⚠️ No Reddit accounts connected. Please connect a Reddit account first.")
        return
    
    # Enhanced search interface
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input(
                "🔍 Search Query*", 
                placeholder="Enter keywords to search for...",
                help="Search for posts containing these keywords"
            )
        
        with col2:
            selected_account = st.selectbox(
                "👤 Account",
                reddit_accounts,
                format_func=lambda x: f"u/{x['username']}"
            )
    
    # Advanced search options
    with st.expander("🔧 Advanced Search Options"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            subreddit = st.text_input(
                "📂 Specific Subreddit", 
                placeholder="e.g., technology",
                help="Search within a specific subreddit"
            )
            
            author = st.text_input(
                "👤 Author",
                placeholder="e.g., username",
                help="Search posts by specific author"
            )
        
        with col2:
            sort_option = st.selectbox("📊 Sort by", ["relevance", "new", "hot", "top", "comments"])
            
            if sort_option == "top":
                time_filter = st.selectbox("⏰ Time Filter", ["hour", "day", "week", "month", "year", "all"])
            else:
                time_filter = None
        
        with col3:
            limit = st.slider("📏 Results Limit", 1, 100, 25)
            
            include_nsfw = st.checkbox("🔞 Include NSFW", value=False)
    
    # Search execution
    col1, col2 = st.columns([1, 4])
    
    with col1:
        search_clicked = st.button("🔍 Search", type="primary", disabled=not query.strip())
    
    with col2:
        if query.strip():
            st.info(f"Ready to search for: '{query.strip()}'")
        else:
            st.warning("Enter a search query to begin")
    
    if search_clicked and query.strip():
        params = {
            "accountId": selected_account['_id'],
            "q": query.strip(),
            "sort": sort_option,
            "limit": limit
        }
        
        if subreddit.strip():
            params["subreddit"] = subreddit.strip()
            params["restrict_sr"] = "1"
        
        if author.strip():
            params["author"] = author.strip()
        
        if time_filter:
            params["t"] = time_filter
        
        if include_nsfw:
            params["include_over_18"] = "1"
        
        with st.spinner("🔍 Searching Reddit..."):
            search_data, error = make_api_request("/reddit/search", params=params)
        
        if search_data:
            items = search_data.get('items', [])
            st.success(f"✅ Found {len(items)} results")
            
            if items:
                # Search results analytics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    avg_score = sum(item.get('score', 0) for item in items) / len(items)
                    st.metric("📊 Avg Score", f"{avg_score:.1f}")
                
                with col2:
                    total_comments = sum(item.get('numComments', 0) for item in items)
                    st.metric("💬 Total Comments", total_comments)
                
                with col3:
                    unique_subreddits = len(set(item.get('subreddit', '') for item in items))
                    st.metric("📂 Subreddits", unique_subreddits)
                
                with col4:
                    unique_authors = len(set(item.get('author', '') for item in items))
                    st.metric("👥 Authors", unique_authors)
                
                st.markdown("---")
                
                # Results display with enhanced formatting
                for i, item in enumerate(items):
                    with st.container():
                        # Result header
                        col1, col2 = st.columns([5, 1])
                        
                        with col1:
                            title = item.get('title', 'Untitled')
                            st.markdown(f"### 📄 {title}")
                        
                        with col2:
                            # Result actions
                            with st.popover("⚙️"):
                                if st.button("📋 Use as Template", key=f"template_{i}"):
                                    st.info("Template functionality coming soon!")
                                if st.button("💾 Save Post", key=f"save_{i}"):
                                    st.info("Save functionality coming soon!")
                        
                        # Post details
                        col1, col2, col3 = st.columns([4, 1, 1])
                        
                        with col1:
                            # Author and subreddit
                            author = item.get('author', 'Unknown')
                            subreddit_name = item.get('subreddit', 'Unknown')
                            st.markdown(f"👤 **u/{author}** in **r/{subreddit_name}**")
                            
                            # Post content
                            selftext = item.get('selftext', '')
                            if selftext:
                                if len(selftext) > 200:
                                    with st.expander("📖 Read full post"):
                                        st.markdown(selftext)
                                    st.markdown(f"{selftext[:200]}...")
                                else:
                                    st.markdown(selftext)
                            
                            # External URL
                            url = item.get('url', '')
                            if url and not url.startswith('https://www.reddit.com'):
                                st.markdown(f"🔗 [External Link]({url})")
                            
                            # Reddit permalink
                            permalink = item.get('permalink', '')
                            if permalink:
                                reddit_url = f"https://reddit.com{permalink}"
                                st.markdown(f"💬 [View on Reddit]({reddit_url})")
                        
                        with col2:
                            # Engagement metrics
                            score = item.get('score', 0)
                            if score > 1000:
                                st.metric("🔥 Score", f"{score/1000:.1f}k")
                            else:
                                st.metric("👍 Score", score)
                        
                        with col3:
                            num_comments = item.get('numComments', 0)
                            if num_comments > 1000:
                                st.metric("💬 Comments", f"{num_comments/1000:.1f}k")
                            else:
                                st.metric("💬 Comments", num_comments)
                            
                            # Engagement ratio
                            if score > 0:
                                ratio = num_comments / score
                                st.metric("📈 Engagement", f"{ratio:.2f}")
                        
                        # Post metadata
                        created_utc = item.get('createdUtc')
                        if created_utc:
                            created_dt = datetime.fromtimestamp(created_utc)
                            time_ago = datetime.now() - created_dt
                            
                            if time_ago.days > 0:
                                st.caption(f"📅 {time_ago.days} days ago")
                            elif time_ago.seconds > 3600:
                                st.caption(f"⏰ {time_ago.seconds//3600} hours ago")
                            else:
                                st.caption(f"⏰ {time_ago.seconds//60} minutes ago")
                        
                        # Post flair
                        flair = item.get('linkFlairText')
                        if flair:
                            st.markdown(f"🏷️ **{flair}**")
                        
                        st.markdown("---")
            else:
                st.info("🔍 No results found. Try different search terms or filters.")
        else:
            st.error(f"❌ Search failed: {error}")

def show_usage_stats():
    """Enhanced usage statistics with visualizations"""
    st.markdown('<div class="section-header">📊 Usage Statistics</div>', unsafe_allow_html=True)
    
    with st.spinner("Loading usage statistics..."):
        usage_data, error = make_api_request("/usage-stats")
    
    if usage_data:
        # Main usage metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📤 Upload Usage")
            uploads = usage_data.get('uploads', {})
            
            current_uploads = uploads.get('current', 0)
            upload_limit = uploads.get('limit', 'Unlimited')
            
            # Upload progress visualization
            if upload_limit != 'Unlimited' and upload_limit > 0:
                progress = current_uploads / upload_limit
                st.progress(progress)
                st.markdown(f"**{current_uploads}/{upload_limit} uploads used** ({progress*100:.1f}%)")
                
                # Warning for high usage
                if progress > 0.8:
                    st.warning("⚠️ Approaching upload limit!")
                elif progress > 0.9:
                    st.error("🚨 Upload limit almost reached!")
            else:
                st.metric("Current Usage", current_uploads)
                st.metric("Limit", upload_limit)
            
            billing_period = uploads.get('billingPeriod', 'monthly')
            st.markdown(f"**Billing Period:** {billing_period.title()}")
            
            last_reset = uploads.get('lastReset')
            if last_reset:
                st.markdown(f"**Last Reset:** {format_datetime(last_reset)}")
        
        with col2:
            st.markdown("#### 👤 Profile Usage")
            profiles = usage_data.get('profiles', {})
            
            current_profiles = profiles.get('current', 0)
            profile_limit = profiles.get('limit', 'N/A')
            
            # Profile progress
            if profile_limit and profile_limit != 'N/A':
                progress = current_profiles / profile_limit
                st.progress(progress)
                st.markdown(f"**{current_profiles}/{profile_limit} profiles used** ({progress*100:.1f}%)")
                
                if progress > 0.8:
                    st.warning("⚠️ Approaching profile limit!")
            else:
                st.metric("Current Profiles", current_profiles)
                st.metric("Profile Limit", profile_limit)
        
        # Additional metrics if available
        if 'api_calls' in usage_data:
            st.markdown("#### 🌐 API Usage")
            api_calls = usage_data['api_calls']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Today", api_calls.get('today', 0))
            with col2:
                st.metric("This Month", api_calls.get('month', 0))
            with col3:
                st.metric("Total", api_calls.get('total', 0))
        
        # Usage tips
        st.markdown("#### 💡 Usage Tips")
        st.markdown("""
        - **Upload Optimization:** Compress images before uploading to save on usage
        - **Profile Management:** Use profiles to organize different types of content
        - **Scheduling:** Batch schedule posts to maximize efficiency
        - **Analytics:** Monitor your usage patterns in the Analytics section
        """)
        
        # Raw data section
        with st.expander("📋 Raw API Response"):
            st.json(usage_data)
    
    else:
        st.error(f"❌ Failed to load usage stats: {error}")

def show_analytics():
    """New analytics page with data visualizations"""
    st.markdown('<div class="section-header">📈 Analytics Dashboard</div>', unsafe_allow_html=True)
    
    # Load posts data for analytics
    posts_data, error = make_api_request("/posts")
    
    if not posts_data or not posts_data.get('posts'):
        st.info("📊 No data available for analytics. Create some posts first!")
        return
    
    posts = posts_data['posts']
    posts_df = pd.DataFrame(posts)
    
    # Convert datetime columns
    if 'createdAt' in posts_df.columns:
        posts_df['createdAt'] = pd.to_datetime(posts_df['createdAt'], errors='coerce')
    
    # Analytics sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Posts by Platform")
        
        # Extract platform data
        platform_data = []
        for post in posts:
            for platform in post.get('platforms', []):
                platform_data.append({
                    'platform': platform.get('platform', 'Unknown').title(),
                    'status': platform.get('status', 'unknown')
                })
        
        if platform_data:
            platform_df = pd.DataFrame(platform_data)
            platform_counts = platform_df['platform'].value_counts()
            
            # Create pie chart
            fig = px.pie(
                values=platform_counts.values,
                names=platform_counts.index,
                title="Posts Distribution by Platform"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No platform data available")
    
    with col2:
        st.markdown("#### 📈 Posts Over Time")
        
        if 'createdAt' in posts_df.columns and not posts_df['createdAt'].isna().all():
            # Group by date
            posts_df['date'] = posts_df['createdAt'].dt.date
            daily_posts = posts_df.groupby('date').size().reset_index(name='count')
            
            # Create line chart
            fig = px.line(
                daily_posts,
                x='date',
                y='count',
                title="Posts Created Over Time",
                markers=True
            )
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Posts"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No date data available")
    
    # Status breakdown
    st.markdown("#### 📋 Post Status Analysis")
    
    status_data = []
    for post in posts:
        for platform in post.get('platforms', []):
            status_data.append({
                'platform': platform.get('platform', 'Unknown').title(),
                'status': platform.get('status', 'unknown').title()
            })
    
    if status_data:
        status_df = pd.DataFrame(status_data)
        status_pivot = status_df.pivot_table(
            index='platform', 
            columns='status', 
            aggfunc=len, 
            fill_value=0
        )
        
        # Create stacked bar chart
        fig = px.bar(
            status_pivot,
            title="Post Status by Platform",
            color_discrete_map={
                'Scheduled': '#3498db',
                'Published': '#2ecc71',
                'Failed': '#e74c3c',
                'Draft': '#f39c12'
            }
        )
        fig.update_layout(
            xaxis_title="Platform",
            yaxis_title="Number of Posts",
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Status summary table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("##### 📊 Detailed Breakdown")
            st.dataframe(status_pivot, use_container_width=True)
        
        with col2:
            # Success rate calculation
            total_posts = len(status_data)
            published_posts = len([s for s in status_data if s['status'] == 'Published'])
            failed_posts = len([s for s in status_data if s['status'] == 'Failed'])
            
            if total_posts > 0:
                success_rate = (published_posts / total_posts) * 100
                st.metric("✅ Success Rate", f"{success_rate:.1f}%")
                
                if failed_posts > 0:
                    failure_rate = (failed_posts / total_posts) * 100
                    st.metric("❌ Failure Rate", f"{failure_rate:.1f}%")
    
    # Content analysis
    st.markdown("#### 📝 Content Analysis")
    
    if posts:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Content length analysis
            content_lengths = [len(post.get('content', '')) for post in posts]
            avg_length = sum(content_lengths) / len(content_lengths)
            max_length = max(content_lengths)
            min_length = min(content_lengths)
            
            st.metric("📏 Avg Content Length", f"{avg_length:.0f} chars")
            st.metric("📏 Max Length", f"{max_length} chars")
            st.metric("📏 Min Length", f"{min_length} chars")
        
        with col2:
            # Media usage
            posts_with_media = len([p for p in posts if p.get('mediaItems')])
            media_percentage = (posts_with_media / len(posts)) * 100
            
            st.metric("🖼️ Posts with Media", posts_with_media)
            st.metric("📊 Media Usage", f"{media_percentage:.1f}%")
        
        with col3:
            # Scheduling analysis
            scheduled_posts = len([p for p in posts if p.get('scheduledFor')])
            immediate_posts = len(posts) - scheduled_posts
            
            st.metric("⏰ Scheduled Posts", scheduled_posts)
            st.metric("🚀 Immediate Posts", immediate_posts)
    
    # Export functionality
    st.markdown("#### 📤 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Analytics CSV"):
            if platform_data:
                csv = pd.DataFrame(platform_data).to_csv(index=False)
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    file_name=f"getlate_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    with col2:
        if st.button("📋 Export Posts JSON"):
            json_data = json.dumps(posts, indent=2)
            st.download_button(
                "⬇️ Download JSON",
                json_data,
                file_name=f"getlate_posts_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
    
    with col3:
        if st.button("📈 Generate Report"):
            st.info("📄 Advanced reporting coming soon!")

def show_accounts_management():
    """New accounts management page"""
    st.markdown('<div class="section-header">🔗 Account Management</div>', unsafe_allow_html=True)
    
    # Load accounts
    if not st.session_state.accounts:
        success, error = load_accounts()
        if not success and error:
            st.error(f"Failed to load accounts: {error}")
            return
    
    # Account connection status
    st.markdown("#### 📊 Connection Overview")
    
    if st.session_state.accounts:
        # Platform summary
        platform_summary = {}
        for account in st.session_state.accounts:
            platform = account.get('platform', 'Unknown')
            status = 'Active' if account.get('isActive', True) else 'Inactive'
            
            if platform not in platform_summary:
                platform_summary[platform] = {'Active': 0, 'Inactive': 0}
            platform_summary[platform][status] += 1
        
        # Display platform cards
        cols = st.columns(min(len(platform_summary), 4))
        
        for i, (platform, counts) in enumerate(platform_summary.items()):
            with cols[i % 4]:
                total = counts['Active'] + counts['Inactive']
                st.metric(
                    f"{get_platform_icon(platform)} {platform.title()}",
                    total,
                    delta=f"{counts['Active']} active"
                )
        
        # Detailed account list
        st.markdown("#### 📋 Account Details")
        
        for account in st.session_state.accounts:
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 3, 2, 1])
                
                with col1:
                    platform = account.get('platform', 'Unknown')
                    st.markdown(f"## {get_platform_icon(platform)}")
                
                with col2:
                    st.markdown(f"**@{account.get('username', 'Unknown')}**")
                    st.markdown(f"*{platform.title()}*")
                    
                    connected_at = account.get('connectedAt')
                    if connected_at:
                        st.caption(f"Connected: {format_datetime(connected_at)}")
                
                with col3:
                    if account.get('isActive', True):
                        st.success("🟢 Active")
                    else:
                        st.error("🔴 Inactive")
                    
                    # Last used
                    last_used = account.get('lastUsed')
                    if last_used:
                        st.caption(f"Last used: {format_datetime(last_used)}")
                
                with col4:
                    if st.button("🔧", key=f"manage_{account['_id']}", help="Manage account"):
                        st.info("Account management coming soon!")
                
                st.markdown("---")
    
    else:
        if error:
            st.error(f"Failed to load accounts: {error}")
        else:
            st.info("🔗 No accounts connected. Visit the GetLate.dev dashboard to connect your accounts.")

# Error handling decorator
def handle_api_errors(func):
    """Decorator to handle common API errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            st.error(f"🌐 Network error: {e}")
        except json.JSONDecodeError:
            st.error("📄 Invalid response format from API")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
    return wrapper

# Add connection testing
def test_api_connection():
    """Test API connection and display results"""
    st.markdown("#### 🔍 API Connection Test")
    
    if st.button("🧪 Run Connection Test"):
        with st.spinner("Testing connection..."):
            test_results = {}
            
            # Test basic endpoints
            endpoints_to_test = [
                ("/profiles", "Profiles"),
                ("/accounts", "Accounts"),
                ("/posts", "Posts"),
                ("/usage-stats", "Usage Stats")
            ]
            
            for endpoint, name in endpoints_to_test:
                data, error = make_api_request(endpoint)
                test_results[name] = {
                    'success': data is not None,
                    'error': error,
                    'response_time': time.time()  # Simplified timing
                }
            
            # Display results
            for name, result in test_results.items():
                if result['success']:
                    st.success(f"✅ {name}: Connected")
                else:
                    st.error(f"❌ {name}: {result['error']}")

# Run the main app
if __name__ == "__main__":
    # Add error boundary
    try:
        main()
    except Exception as e:
        st.error(f"🚨 Application Error: {e}")
        st.markdown("Please refresh the page or contact support if the issue persists.")
        
        with st.expander("🔧 Debug Information"):
            st.code(str(e))
            
        # Connection test in error state
        if st.session_state.api_key:
            test_api_connection()
