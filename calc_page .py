import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import json

# --- GEMINI AI CONFIGURATION ---
# IMPORTANT: Your API key is visible here. For production, use st.secrets.
# I have left your key here as requested, but please be aware of the security risks.
GEMINI_API_KEY = "AIzaSyCx7gfigfB0nEu2nZ-LGUNLnAuKcN8iWrk" 
# --- END GEMINI CONFIGURATION ---


def get_gemini_response(chat_history: list):
    """
    Sends a conversation history to the Gemini API using a direct HTTP request.

    Args:
        chat_history (list): A list of dictionaries representing the conversation.
                             Example: [{"role": "user", "parts": [{"text": "Hello"}]}]

    Returns:
        str: The text response from the AI model, or an error message.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return "Error: Gemini API key is not configured. Please set it at the top of the script."

    model_name = "gemini-1.5-flash-latest" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": chat_history,
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status() 
        
        response_json = response.json()
        
        if "candidates" not in response_json:
            prompt_feedback = response_json.get("promptFeedback", {})
            block_reason = prompt_feedback.get("blockReason", "Unknown")
            return f"Error: The AI model blocked the request, likely due to safety filters. Reason: {block_reason}"

        candidates = response_json.get("candidates", [])
        if not candidates:
            return "Error: The AI model returned no candidates. This may be due to safety filters or an API issue."
            
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "Error: The AI model's response was empty."

        return parts[0].get("text", "Error: Could not extract text from the AI response.")

    except requests.exceptions.HTTPError as http_err:
        error_details = response.json().get("error", {})
        error_message = error_details.get("message", "No specific error message provided.")
        return f"**Error: An HTTP error occurred while contacting the Gemini API.**\n\n*Details:* {error_message}"
    except requests.exceptions.RequestException as e:
        return f"**Error: A network error occurred.** Please check your connection. \n\n*Details:* {e}"
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"**Error: Could not parse the AI's response.** It may be malformed. \n\n*Details:* {e}"


st.set_page_config(page_title="Interface", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🌍 CO2 Footprint Calculator")
st.write("Calculate your carbon footprint and see the impact of green energy.")

with st.form("co2_form"):
    st.markdown("### 🚗 Transportation Details")

    col1, col2 = st.columns(2)
    with col1:
        cars = st.number_input("Number of Cars", value=0, step=1)
        if cars < 0:
            st.error("❌ Number of cars must be greater than 0")

    with col2:
        passengers = st.number_input("Number of Passengers", value=0, step=1)
        if passengers < 0:
            st.error("❌ Number of passengers must be greater than 0")

    containers = st.number_input("Number of Containers", value=0, step=1)
    if containers < 0:
        st.error("❌ Number of containers must be greater than 0")

    if cars <= 0 and passengers <= 0 and containers <= 0:
        st.warning("⚠️ Please provide at least one transportation value (cars, passengers, or containers) greater than 0.")

    st.markdown("### 🍃 Green Energy (Optional)")
    col1, col2, col3 = st.columns(3)
    with col1:
        solar = st.number_input("Solar Energy (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)
    with col2:
        wind = st.number_input("Wind Energy (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)
    with col3:
        hydro = st.number_input("Hydro Energy (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)

    total_renewable = solar + wind + hydro

    if total_renewable == 0:
        st.info("ℹ️ You haven't used any green energy sources. Default coefficient will be used.")


    elif total_renewable > 100:
        st.error(f"❌ Error: Total green energy percentage cannot exceed 100%. Current total: {total_renewable:.1f}%")
    else:
        st.markdown(
    f"""
    <div style="
    background-color: #415D43;
    color: #E8F5E9;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 0px;  <!-- Set to 0 since we'll use BR -->
    border-left: 6px solid #A5D6A7;
    font-family: 'sans-serif';
    ">
    ✅ Total Green Energy: <strong>{total_renewable:.1f}%</strong>
    </div>
    <br>  <!-- Adds two line breaks -->
    """,
    unsafe_allow_html=True
)

    submitted = st.form_submit_button("✅ Calculate CO2 Footprint and Analyze")
    
    if submitted:
            if total_renewable > 100:
                st.warning("🚫 Please correct the green energy input before calculating.")
           


if submitted and total_renewable <= 100 and (cars > 0 or passengers > 0 or containers > 0):
    st.session_state.messages = []

    st.markdown("## 📈 CO2 Emission Table")

    CO2_PER_CAR, CO2_PER_PASSENGER, CO2_PER_CONTAINER = 0.87, 0.25, 10.21
    COAL_PER_CAR, COAL_PER_PASSENGER, COAL_PER_CONTAINER = 1.25, 0.36, 14.71
    SOLAR_COEF, WIND_COEF, HYDRO_COEF, DEFAULT_GREEN_COEF = 0.012, 0.011, 0.004, 0.03385

    def calc_green_coef(solar, wind, hydro):
        total = solar + wind + hydro
        if total == 0: return DEFAULT_GREEN_COEF
        return ((solar/total)*SOLAR_COEF + (wind/total)*WIND_COEF + (hydro/total)*HYDRO_COEF)

    def calc_green_emission(co2): return co2 * calc_green_coef(solar, wind, hydro)

    data, total_co2, total_coal, total_green = [], 0, 0, 0
    if cars > 0:
        co2_val = cars * CO2_PER_CAR; green = calc_green_emission(co2_val)
        data.append(["Car", cars, co2_val, cars * COAL_PER_CAR, green]); total_co2 += co2_val; total_green += green
    if passengers > 0:
        co2_val = passengers * CO2_PER_PASSENGER; green = calc_green_emission(co2_val)
        data.append(["Passenger", passengers, co2_val, passengers * COAL_PER_PASSENGER, green]); total_co2 += co2_val; total_green += green
    if containers > 0:
        co2_val = containers * CO2_PER_CONTAINER; green = calc_green_emission(co2_val)
        data.append(["Container", containers, co2_val, containers * COAL_PER_CONTAINER, green]); total_co2 += co2_val; total_green += green

    df = pd.DataFrame(data, columns=["Type", "Quantity", "Total CO₂ (kg)", "Total Coal CO₂ (kg)", "Green Energy CO₂ (kg)"])
    st.table(df.style.format("{:.2f}", subset=df.columns[2:]))
    reduction = (1 - total_green / total_co2) * 100 if total_co2 != 0 else 0

    tab1, tab2, tab3 = st.tabs(["📊 Comparison", "📈 Visualization", "🧠 AI Chat"])

    # ++++++++++++++++++++++++++++++++++++++
    # --- RESTORED ORIGINAL COMPARISON TAB ---
    # ++++++++++++++++++++++++++++++++++++++
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.error("🔺 Without Green Energy")
            st.markdown(f"<h2 style='color:red;'>{total_co2:.2f} kg CO₂</h2>", unsafe_allow_html=True)
        with col2:
            st.success("🌱 With Green Energy")
            st.markdown(f"<h2 style='color:green;'>{total_green:.2f} kg CO₂</h2>", unsafe_allow_html=True)

        st.markdown("### 🧮 Reduction Impact")
        
        safe_reduction = max(0, min(int(reduction), 100))
        st.markdown("High Positive Impact")
        st.progress(safe_reduction)
        st.caption(f"{reduction:.0f}% reduction")

        with st.expander("🔍 Details", expanded=True):
            st.markdown("#### Input Details:")
            if cars > 0: st.write(f"🚗 Cars: {cars}")
            if passengers > 0: st.write(f"🧍 Passengers: {passengers}")
            if containers > 0: st.write(f"📦 Containers: {containers}")
            st.write(f"🔋 Solar Energy: {solar}%")
            st.write(f"🌬️ Wind Energy: {wind}%")
            st.write(f"💧 Hydro Energy: {hydro}%")

            st.markdown("#### 🌎 Environmental Impact:")
            st.markdown(f"""<div style='background-color:rgba(248, 215, 218, 0.85); color:#721c24; padding:10px; border-radius:8px;'><strong>🚨 High CO2 Emissions Impact</strong><br>The <b>{total_co2:.0f} kg</b> of CO₂ emissions contribute to global warming and pollution.</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div style='background-color:rgba(215, 248, 222, 0.85); color:#1c7224; padding:10px; border-radius:8px; margin-top:10px;'><strong>🌿 Green Energy Benefits</strong><br>By reducing emissions to <b>{total_green:.0f} kg CO₂</b> with renewables, you're helping protect our planet.</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div style='background-color:rgba(215, 230, 248, 0.85); color:#1c2472; padding:10px; border-radius:8px; margin-top:10px;'><strong>🔍 Why This Matters</strong><br>Every kilogram of CO₂ avoided makes a difference in fighting climate change.</div><br>""", unsafe_allow_html=True)

    with tab2:
        st.subheader("📉 Emission Sources by Transport Type")
        detailed_data = pd.DataFrame([
            {"Type": "Car", "Emission Source": "Total CO₂", "Emissions (kg)": cars * CO2_PER_CAR},
            {"Type": "Car", "Emission Source": "Coal-based CO₂", "Emissions (kg)": cars * COAL_PER_CAR},
            {"Type": "Car", "Emission Source": "Green Energy CO₂", "Emissions (kg)": round(calc_green_emission(cars * CO2_PER_CAR), 2)},
            {"Type": "Passenger", "Emission Source": "Total CO₂", "Emissions (kg)": passengers * CO2_PER_PASSENGER},
            {"Type": "Passenger", "Emission Source": "Coal-based CO₂", "Emissions (kg)": passengers * COAL_PER_PASSENGER},
            {"Type": "Passenger", "Emission Source": "Green Energy CO₂", "Emissions (kg)": round(calc_green_emission(passengers * CO2_PER_PASSENGER), 2)},
            {"Type": "Container", "Emission Source": "Total CO₂", "Emissions (kg)": containers * CO2_PER_CONTAINER},
            {"Type": "Container", "Emission Source": "Coal-based CO₂", "Emissions (kg)": containers * COAL_PER_CONTAINER},
            {"Type": "Container", "Emission Source": "Green Energy CO₂", "Emissions (kg)": round(calc_green_emission(containers * CO2_PER_CONTAINER), 2)},
        ])
        fig = px.bar(detailed_data, x="Type", y="Emissions (kg)", color="Emission Source", barmode="group", text="Emissions (kg)", color_discrete_map={"Total CO₂": "#FFE6E1", "Coal-based CO₂": "#FF3F33", "Green Energy CO₂": "#9FC87E"}, title="Grouped CO₂ Emissions by Transport Type")
        fig.update_traces(texttemplate='%{text:.2f}')
        fig.update_layout(xaxis_title="Transport Type", yaxis_title="CO₂ Emissions (kg)", title_x=0.3, plot_bgcolor='rgba(0,0,0,0)', bargap=0.3)
        st.plotly_chart(fig, use_container_width=True)

    # ++++++++++++++++++++++++++++++++++++++
    # --- AI CHAT TAB WITH CLICKABLE EXPANDER ---
    # ++++++++++++++++++++++++++++++++++++++
    with tab3:
        st.subheader("🤖 AI-Powered Analysis & Chat")

        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            st.warning("⚠️ Please configure your Gemini API key at the top of the script to enable the AI chat.")
        else:
            if not st.session_state.messages:
                with st.spinner("🧠 The AI is generating your personalized analysis..."):
                    initial_prompt_text = f"""
                    You are an expert analyst in climate science. Your task is to provide a two-part analysis of a user's carbon footprint.

                    **User's Input Data:**
                    - Cars: {cars}, Passengers: {passengers}, Containers: {containers}
                    - Green Energy Mix: {solar}% Solar, {wind}% Wind, {hydro}% Hydro.

                    **Calculated Results:**
                    - Before Green Energy: {total_co2:.2f} kg CO₂
                    - After Green Energy: {total_green:.2f} kg CO₂
                    - Reduction: {reduction:.2f}%

                    **YOUR TASK:**
                    First, create a "Concise Summary". Each point in the summary must be short and impactful (1-2 sentences).
                    Then, add the separator '---DETAILED_ANALYSIS_BELOW---' on its own line.
                    Finally, write a "Full Deep-Dive Analysis" using detailed paragraphs, bullet points, and Markdown formatting.

                    **PART 1: CONCISE SUMMARY (WRITE THIS FIRST)**
                    - **Overall Impact:** Briefly state the 'before' and 'after' CO2 numbers and the percentage reduction.
                    - **Main Emission Source:** Identify the single biggest contributor to their emissions.
                    - **Key Takeaway:** Give one sentence of encouragement or the most important finding.

                    ---DETAILED_ANALYSIS_BELOW---

                    **PART 2: FULL DEEP-DIVE ANALYSIS (WRITE THIS SECOND)**
                    ### 🔍 In-Depth Analysis
                    - **Executive Summary:** Start with an impactful paragraph summarizing the results.
                    - **Emission Hotspot:** Elaborate on the main source of emissions you identified. Explain why it's so high.
                    - **The Power of Your Green Mix:** Detail how their chosen mix of solar, wind, and hydro achieved the {reduction:.2f}% reduction.
                    
                    ### 🔮 Future Projections
                    - **Annual Impact:** Assuming this is a daily activity, calculate and project the annual CO2 emissions for both 'before' and 'after' scenarios. Frame the annual savings in a powerful way (e.g., "equivalent to planting X trees").

                    ### 🌱 Actionable Recommendations
                    1.  **Source Reduction:** Suggest a specific way to reduce emissions from their main source.
                    2.  **Green Mix Optimization:** Advise them on how to adjust their energy mix for even lower emissions, referencing the coefficients (Solar={SOLAR_COEF}, Wind={WIND_COEF}, Hydro={HYDRO_COEF}).
                    3.  **Broader Tip:** Offer a general lifestyle tip related to sustainability.
                    """
                    
                    initial_api_call_history = [{"role": "user", "parts": [{"text": initial_prompt_text}]}]
                    ai_response = get_gemini_response(initial_api_call_history)
                    
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

            for i, message in enumerate(st.session_state.messages):
                with st.chat_message(message["role"]):
                    if i == 0 and message["role"] == "assistant":
                        full_content = message["content"]
                        separator = "---DETAILED_ANALYSIS_BELOW---"

                        if separator in full_content:
                            summary, _, detailed_analysis = full_content.partition(separator)
                            st.markdown(summary)
                            with st.expander("🔍 Click here to read the full deep-dive analysis..."):
                                st.markdown(detailed_analysis)
                        else:
                            st.markdown(full_content)
                    else:
                        st.markdown(message["content"])

            if prompt := st.chat_input("Ask a follow-up question..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        api_history = [
                            {"role": "model" if msg["role"] == "assistant" else "user", "parts": [{"text": msg["content"]}]}
                            for msg in st.session_state.messages
                        ]
                        
                        response = get_gemini_response(api_history)
                        st.markdown(response)
                
                st.session_state.messages.append({"role": "assistant", "content": response})

