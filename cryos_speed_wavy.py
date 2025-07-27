import streamlit as st
import speedtest
import time
import numpy as np
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import json
import requests
import statistics

# Set page configuration
st.set_page_config(
    page_title="Cryos - Network Suitability Analyzer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply enhanced styling
def local_css():
    st.markdown("""
        <style>
        /* Main Theme */
        .main {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            color: #E0E0E0;
        }
        
        /* Card styling */
        .css-1r6slb0 {
            background: rgba(21, 67, 96, 0.6);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            margin-bottom: 20px;
        }
        
        /* Button styling */
        .stButton button {
            background: linear-gradient(45deg, #00b4db, #0083b0);
            color: white;
            font-weight: bold;
            border-radius: 10px;
            padding: 0.75em 2em;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
            transition: all 0.3s ease;
            border: none;
        }
        .stButton button:hover {
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.8);
            transform: scale(1.05);
            background: linear-gradient(45deg, #00c4db, #00a3c0);
        }
        
        /* Metric cards */
        .metric-container {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            text-align: center;
            border: 1px solid rgba(0, 255, 255, 0.1);
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #00FFFF;
        }
        .metric-label {
            font-size: 16px;
            color: #A0A0A0;
        }
        
        /* Use case cards */
        .use-case-card {
            background: rgba(0, 30, 60, 0.7);
            border-radius: 12px;
            padding: 15px;
            height: 100%;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .use-case-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        }
        .use-case-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #00FFFF;
        }
        .use-case-body {
            font-size: 14px;
            color: #E0E0E0;
        }
        
        /* Headers */
        h1, h2, h3 {
            background: linear-gradient(90deg, #00FFFF, #0088FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: bold;
        }
        
        /* Dividers */
        hr {
            border-color: rgba(0, 255, 255, 0.2);
            margin: 30px 0;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 20px;
            color: #A0A0A0;
            font-size: 14px;
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# Helper functions for animated elements
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Load animations
loading_animation = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_p8bfn5to.json")

# Create animated speedometer
def create_speedometer(value, max_value, title, units, color_scale, is_inverse=False):
    """
    Create a speedometer gauge with proper color scaling
    is_inverse=True means lower values are better (for ping and jitter)
    """
    # For inverse metrics (ping, jitter), reverse the color scale
    if is_inverse:
        color_scale = color_scale[::-1]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 24, 'color': '#00FFFF'}},
        delta={'reference': max_value/2 if not is_inverse else max_value/2, 
               'increasing': {'color': "#00FFFF" if not is_inverse else "#FF5555"},
               'decreasing': {'color': "#00FFFF" if is_inverse else "#FF5555"}},
        gauge={
            'axis': {'range': [None, max_value], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#00FFFF"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, max_value/3], 'color': color_scale[0]},
                {'range': [max_value/3, 2*max_value/3], 'color': color_scale[1]},
                {'range': [2*max_value/3, max_value], 'color': color_scale[2]}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "white", 'family': "Arial"},
        annotations=[
            dict(
                text=f"{units}",
                x=0.5,
                y=0.25,
                font=dict(size=16, color="#00FFFF"),
                showarrow=False,
                xanchor="center"
            )
        ]
    )
    
    # Add animation effects
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                buttons=[
                    dict(
                        label="Animate",
                        method="animate",
                        args=[None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True}]
                    )
                ],
                visible=False
            )
        ]
    )
    
    return fig

# Function to measure jitter properly
def measure_jitter(num_pings=10):
    """
    Measure network jitter by running multiple pings and calculating the standard deviation
    This is a more accurate way to measure jitter than the original random approach
    """
    try:
        # Initialize lists to store ping times
        ping_times = []
        
        # Use speedtest's get_best_server and ping methods multiple times
        test = speedtest.Speedtest()
        server = test.get_best_server()
        
        # Get multiple ping measurements
        for _ in range(num_pings):
            test = speedtest.Speedtest()
            test.get_best_server()
            ping_times.append(test.results.ping)
            time.sleep(0.2)  # Short delay between pings
        
        # Calculate jitter as the standard deviation of ping times
        if len(ping_times) > 1:
            jitter = statistics.stdev(ping_times)
        else:
            jitter = 0.0
            
        # Get the average ping for reporting
        avg_ping = statistics.mean(ping_times)
        
        return avg_ping, jitter
    except Exception as e:
        # If there's an error, return reasonable defaults
        st.warning(f"Error measuring jitter: {e}")
        return 50.0, 5.0

# Cryos Header with enhanced design
st.markdown("""
    <div style="text-align:center; padding: 20px 0;">
        <h1 style='font-size: 3em; margin-bottom: 0;'>🚀 Cryos</h1>
        <h2 style='margin-top: 0; font-size: 1.8em; font-weight: normal;'>Network Suitability Analyzer</h2>
        <p style='font-size: 1.2em; opacity: 0.8;'>Experience blazing-fast connectivity testing with analysis tailored to your digital lifestyle</p>
    </div>
""", unsafe_allow_html=True)

# Create a card for the speed test
st.markdown("""
    <div class="css-1r6slb0">
        <h3 style="text-align: center;">📡 Start Your Speed Test</h3>
    </div>
""", unsafe_allow_html=True)

# Center the button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    start_test = st.button("Run Speed Test", use_container_width=True)

# Initialize session state for animated testing
if 'test_progress' not in st.session_state:
    st.session_state.test_progress = 0
if 'test_complete' not in st.session_state:
    st.session_state.test_complete = False
if 'download' not in st.session_state:
    st.session_state.download = 0
if 'upload' not in st.session_state:
    st.session_state.upload = 0
if 'ping' not in st.session_state:
    st.session_state.ping = 0
if 'jitter' not in st.session_state:
    st.session_state.jitter = 0

# Speedometer container
speedometer_container = st.container()

# Results container
results_container = st.container()

# Analysis container
analysis_container = st.container()

# Suggestions container
suggestions_container = st.container()

if start_test:
    # Reset state
    st.session_state.test_complete = False
    st.session_state.test_progress = 0
    
    # Show loading animation
    with speedometer_container:
        st_lottie(loading_animation, height=200, key="loading")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simulate the testing process
        status_text.text("Initializing speed test...")
        time.sleep(1)
        
        try:
            # Connecting to servers
            status_text.text("Finding optimal server...")
            progress_bar.progress(10)
            test = speedtest.Speedtest()
            test.get_best_server()
            time.sleep(1)
            
            # First measure ping and jitter
            status_text.text("Measuring ping and jitter...")
            progress_bar.progress(30)
            
            # Use proper jitter measurement instead of random values
            ping, jitter = measure_jitter(num_pings=5)
            st.session_state.ping = ping
            st.session_state.jitter = jitter
            status_text.text(f"Ping: {ping:.2f} ms, Jitter: {jitter:.2f} ms")
            time.sleep(1)
            
            # Download test
            status_text.text("Testing download speed...")
            progress_bar.progress(50)
            
            # Simulate real-time updating
            for i in range(50, 70):
                time.sleep(0.05)
                progress_bar.progress(i)
                
            download = test.download() / 1_000_000
            st.session_state.download = download
            status_text.text(f"Download speed: {download:.2f} Mbps")
            time.sleep(1)
            
            # Upload test
            status_text.text("Testing upload speed...")
            progress_bar.progress(70)
            
            # Simulate real-time updating
            for i in range(70, 95):
                time.sleep(0.05)
                progress_bar.progress(i)
                
            upload = test.upload() / 1_000_000
            st.session_state.upload = upload
            status_text.text(f"Upload speed: {upload:.2f} Mbps")
            time.sleep(1)
            
            # Complete
            progress_bar.progress(100)
            status_text.text("Test completed successfully!")
            st.session_state.test_complete = True
            
        except Exception as e:
            status_text.text(f"An error occurred: {e}")
            st.error(f"Speed test failed: {e}")

# Display results once test is complete
if st.session_state.test_complete:
    with speedometer_container:
        st.empty()  # Clear the loading animation
        
        # Create speedometer display
        st.markdown("## 📊 Test Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Download speedometer
            download_fig = create_speedometer(
                st.session_state.download, 
                max(100, st.session_state.download * 1.5), 
                "Download", 
                "Mbps",
                ["rgba(150, 50, 0, 0.8)", "rgba(0, 100, 150, 0.8)", "rgba(0, 150, 200, 0.8)"]
            )
            st.plotly_chart(download_fig, use_container_width=True)
            
            # Ping speedometer - lower is better so use is_inverse=True
            ping_fig = create_speedometer(
                st.session_state.ping, 
                150, 
                "Ping", 
                "ms",
                ["rgba(0, 150, 200, 0.8)", "rgba(0, 100, 150, 0.8)", "rgba(150, 50, 0, 0.8)"],
                is_inverse=True
            )
            st.plotly_chart(ping_fig, use_container_width=True)
            
        with col2:
            # Upload speedometer
            upload_fig = create_speedometer(
                st.session_state.upload, 
                max(50, st.session_state.upload * 1.5), 
                "Upload", 
                "Mbps",
                ["rgba(150, 50, 0, 0.8)", "rgba(0, 100, 150, 0.8)", "rgba(0, 150, 200, 0.8)"]
            )
            st.plotly_chart(upload_fig, use_container_width=True)
            
            # Jitter speedometer - lower is better so use is_inverse=True
            jitter_fig = create_speedometer(
                st.session_state.jitter, 
                30, 
                "Jitter", 
                "ms",
                ["rgba(0, 150, 200, 0.8)", "rgba(0, 100, 150, 0.8)", "rgba(150, 50, 0, 0.8)"],
                is_inverse=True
            )
            st.plotly_chart(jitter_fig, use_container_width=True)
            
    # Network Suitability Analyzer with improved grid layout
    with analysis_container:
        st.markdown("## 🔍 Network Suitability Analyzer")
        
        def get_status(category, thresholds, inverse=False):
            """
            Get status based on thresholds
            inverse=True means lower values are better (for ping and jitter)
            """
            if category == "download":
                value = st.session_state.download
            elif category == "upload":
                value = st.session_state.upload
            elif category == "ping":
                value = st.session_state.ping
            elif category == "jitter":
                value = st.session_state.jitter
            else:
                return "unknown"
                
            if inverse:
                # For inverse metrics (ping, jitter) - lower is better
                if value <= thresholds[0]:
                    return "good"
                elif value <= thresholds[1]:
                    return "moderate"
                else:
                    return "bad"
            else:
                # For regular metrics (download, upload) - higher is better
                if value >= thresholds[0]:
                    return "good"
                elif value >= thresholds[1]:
                    return "moderate"
                else:
                    return "bad"
        
        def create_use_case_card(title, icon, category_checks, good_msg, mod_msg, bad_msg):
            status = "good"
            
            # Check all the requirements
            for cat, thresholds in category_checks.items():
                inverse = cat in ["ping", "jitter"]  # Ping and jitter are inverse metrics
                cat_status = get_status(cat, thresholds, inverse)
                if cat_status == "bad":
                    status = "bad"
                    break
                elif cat_status == "moderate" and status != "bad":
                    status = "moderate"
            
            # Determine styling and message
            if status == "good":
                color = "#00FF00"
                emoji = "✅"
                message = good_msg
                bg_color = "rgba(0, 100, 0, 0.3)"
            elif status == "moderate":
                color = "#FFAA00"
                emoji = "⚠️"
                message = mod_msg
                bg_color = "rgba(100, 70, 0, 0.3)"
            else:
                color = "#FF0000"
                emoji = "❌"
                message = bad_msg
                bg_color = "rgba(100, 0, 0, 0.3)"
                
            return f"""
                <div class="use-case-card" style="background: {bg_color};">
                    <div class="use-case-title">
                        {icon} {title} {emoji}
                    </div>
                    <div class="use-case-body">
                        {message}
                    </div>
                </div>
            """
        
        # Define the use cases in a 3x3 grid
        # Note: For ping and jitter, the thresholds work in reverse (lower is better)
        use_cases = [
            {
                "title": "Video Streaming",
                "icon": "📺",
                "checks": {"download": [25, 10]},
                "good_msg": "Excellent! 4K HDR content will stream fluidly.",
                "mod_msg": "Suitable for 720p-1080p. Multiple users may experience buffering.",
                "bad_msg": "Too slow for smooth video playback. Expect frequent buffering."
            },
            {
                "title": "Gaming / AR-VR",
                "icon": "🎮",
                "checks": {"ping": [30, 80], "jitter": [5, 15]},
                "good_msg": "Perfect for competitive gaming and real-time VR applications.",
                "mod_msg": "Acceptable for casual games but may experience occasional lag in fast-paced titles.",
                "bad_msg": "High latency will cause significant lag in most games and VR apps."
            },
            {
                "title": "Video Calls",
                "icon": "🎥",
                "checks": {"upload": [5, 2], "download": [5, 2]},
                "good_msg": "Crisp HD video calls with multiple participants supported.",
                "mod_msg": "Standard definition calls possible with occasional quality drops.",
                "bad_msg": "Likely to experience freezing, pixelation and audio issues."
            },
            {
                "title": "Industry 4.0 / IoT",
                "icon": "🏭",
                "checks": {"ping": [20, 50], "upload": [10, 5], "jitter": [3, 10]},
                "good_msg": "Ideal for industrial automation and real-time cloud sync.",
                "mod_msg": "Usable for basic industrial applications with modest data needs.",
                "bad_msg": "Too unreliable for critical industrial applications."
            },
            {
                "title": "Banking / Transactions",
                "icon": "🏦",
                "checks": {"ping": [80, 150], "jitter": [10, 20]},
                "good_msg": "Fast and responsive for secure financial transactions.",
                "mod_msg": "Transactions will work but with slight delays.",
                "bad_msg": "Connection may time out during sensitive operations."
            },
            {
                "title": "Healthcare / Telemedicine",
                "icon": "🏥",
                "checks": {"download": [15, 5], "upload": [3, 1], "ping": [50, 100], "jitter": [5, 15]},
                "good_msg": "Perfect for telemedicine consultations and medical image sharing.",
                "mod_msg": "Basic telemedicine possible but image quality may be reduced.",
                "bad_msg": "Not reliable enough for critical healthcare applications."
            },
            {
                "title": "Smart City Infrastructure",
                "icon": "🌆",
                "checks": {"upload": [10, 3], "ping": [30, 80], "jitter": [5, 15]},
                "good_msg": "Excellent for smart city sensors, traffic management and public safety systems.",
                "mod_msg": "Can support basic smart city functions with limited real-time capabilities.",
                "bad_msg": "Too unstable for reliable smart city infrastructure."
            },
            {
                "title": "Research & Data Science",
                "icon": "🔬",
                "checks": {"download": [50, 20], "upload": [20, 10]},
                "good_msg": "Perfect for cloud computing, large dataset transfers and collaborative research.",
                "mod_msg": "Usable for moderate research needs but large data transfers will be slow.",
                "bad_msg": "Data-intensive research will be significantly hampered."
            },
            {
                "title": "Remote Work",
                "icon": "💼",
                "checks": {"download": [15, 5], "upload": [5, 2], "ping": [100, 200], "jitter": [10, 20]},
                "good_msg": "Excellent for all remote work needs including collaborative tools.",
                "mod_msg": "Suitable for basic remote work but may struggle with video meetings.",
                "bad_msg": "Remote work will be challenging with frequent connectivity issues."
            }
        ]
        
        # Create the grid
        st.markdown("<h3 style='text-align:center;'>🧠 Use Case Analysis</h3>", unsafe_allow_html=True)
        
        # Display in rows of 3
        for i in range(0, len(use_cases), 3):
            cols = st.columns(3)
            for j in range(3):
                if i+j < len(use_cases):
                    case = use_cases[i+j]
                    cols[j].markdown(
                        create_use_case_card(
                            case["title"], 
                            case["icon"], 
                            case["checks"],
                            case["good_msg"],
                            case["mod_msg"],
                            case["bad_msg"]
                        ), 
                        unsafe_allow_html=True
                    )
    
    # Enhanced suggestions
    with suggestions_container:
        st.markdown("## 💡 Personalized Improvement Suggestions")
        
        suggestions = []
        
        # Add download speed suggestions
        if st.session_state.download < 10:
            suggestions.append({
                "icon": "🔽",
                "title": "Critically Low Download Speed",
                "content": "Your download speed is severely limiting your online activities. Consider upgrading to at least a 50 Mbps plan for general use, or 100+ Mbps for households with multiple users."
            })
        elif st.session_state.download < 25:
            suggestions.append({
                "icon": "🔽",
                "title": "Low Download Speed",
                "content": "Your download speed may limit streaming quality and large file downloads. Consider upgrading your plan or checking for network interference."
            })
            
        # Add upload speed suggestions
        if st.session_state.upload < 2:
            suggestions.append({
                "icon": "🔼",
                "title": "Critically Low Upload Speed",
                "content": "Your upload speed will severely impact video calls, file sharing, and cloud backups. Contact your ISP about asymmetric connection options or business-grade plans with better upload speeds."
            })
        elif st.session_state.upload < 5:
            suggestions.append({
                "icon": "🔼",
                "title": "Low Upload Speed",
                "content": "Your upload speed may impact video conferencing and file sharing. Consider a plan with better upload capacity if you frequently use these services."
            })
            
        # Add latency suggestions
        if st.session_state.ping > 100:
            suggestions.append({
                "icon": "⏱️",
                "title": "High Latency Detected",
                "content": "Your high ping will impact gaming, video calls, and real-time applications. Try using a wired Ethernet connection instead of WiFi, and ensure no other bandwidth-heavy applications are running."
            })
            
        # Add jitter suggestions
        if st.session_state.jitter > 10:
            suggestions.append({
                "icon": "📶",
                "title": "Connection Instability",
                "content": "Your connection shows significant jitter (variation in ping), which can cause unstable performance even with good speeds. Check for interference sources, outdated router firmware, or try a mesh WiFi system for better coverage."
            })
            
        # Add general suggestions
        suggestions.append({
            "icon": "🛠️",
            "title": "Connection Optimization",
            "content": "For best performance: (1) Use wired connections for stationary devices, (2) Place your router in a central, elevated location, (3) Use 5GHz WiFi for devices that support it, (4) Regularly restart your modem and router."
        })
        
        suggestions.append({
            "icon": "📱",
            "title": "Device Optimization",
            "content": "Ensure your devices are updated with the latest firmware and drivers. Close background applications that may be consuming bandwidth. Consider upgrading older devices that may have limited WiFi capabilities."
        })
        
        # Display suggestions in a 2-column grid
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            col_idx = i % 2
            with cols[col_idx]:
                st.markdown(f"""
                    <div style="background: rgba(0, 60, 120, 0.3); border-radius: 10px; padding: 15px; margin-bottom: 15px; border-left: 4px solid #00FFFF;">
                        <h4 style="color: #00FFFF; margin-top: 0;">{suggestion['icon']} {suggestion['title']}</h4>
                        <p style="margin-bottom: 0;">{suggestion['content']}</p>
                    </div>
                """, unsafe_allow_html=True)

# Meet the Creators with improved styling
st.markdown("## 👨‍💻 Meet the Creators of Cryos")

creator_col1, creator_col2 = st.columns(2)

with creator_col1:
    st.markdown("""
        <div style="background: rgba(0, 30, 60, 0.7); border-radius: 15px; padding: 20px; height: 100%; border: 1px solid rgba(0, 255, 255, 0.3);">
            <h3 style="margin-top: 0;">🌌 Saksham Anand</h3>
            <p>A tech enthusiast passionate about building innovative digital experiences that enhance everyday connectivity.</p>
            <div style="display: flex; gap: 10px;">
                <a href="https://github.com/SakshamAnand/" style="text-decoration: none; color: #00FFFF;">🔗 GitHub</a>
                <a href="https://www.linkedin.com/in/saksham-anand05/" style="text-decoration: none; color: #00FFFF;">🔗 LinkedIn</a>
            </div>
        </div>
    """, unsafe_allow_html=True)


# Enhanced footer
st.markdown("""
    <div class="footer">
        <hr>
        <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 10px;">
            <a href="#" style="text-decoration: none; color: #00FFFF;">🔗 Twitter</a>
            <a href="#" style="text-decoration: none; color: #00FFFF;">🔗 GitHub</a>
            <a href="#" style="text-decoration: none; color: #00FFFF;">🔗 LinkedIn</a>
            <a href="#" style="text-decoration: none; color: #00FFFF;">📧 Contact</a>
            <a href="#" style="text-decoration: none; color: #00FFFF;">📄 About</a>
        </div>
        <p style="margin: 0; padding: 10px 0;">© 2025 Cryos. All rights reserved.</p>
        <p style="margin: 0; font-size: 12px; opacity: 0.7;">Empowering the world with better connectivity insights.</p>
    </div>
""", unsafe_allow_html=True)
