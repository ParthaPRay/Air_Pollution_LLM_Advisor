# Air Pollution LLM Advisor
# Partha Pratim Ray, 24 June, 2025
# parthapratimray1986@gmail.com

import re
import csv
import os
import folium
import gradio as gr
import requests
import datetime

# --- Helper to remove units ---
def remove_units(val):
    if val is None:
        return ""
    m = re.search(r"[-+]?\d*\.\d+|\d+", str(val))
    return m.group(0) if m else val

# --- CSV logger ---
def append_llm_csv_row(
    timestamp, location, lat, lon, pollution_data, methane_csv, llm_name, llm_response, ollama_metrics
):
    filename = "llm_aqi_log.csv"
    columns = [
        "timestamp", "location", "lat", "lon",
        "PM2.5", "PM10", "CO", "NO2", "SO2", "O3",
        "AOD", "Dust", "UV Index", "UV Index clear sky", "Methane",
        "llm", "llm_response",
        "total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration",
        "eval_count", "eval_duration", "tokens_per_second"
    ]
    file_exists = os.path.isfile(filename)
    row = [
        timestamp, location, lat, lon,
        remove_units(pollution_data.get("PM₂.₅", "")),
        remove_units(pollution_data.get("PM₁₀", "")),
        remove_units(pollution_data.get("CO", "")),
        remove_units(pollution_data.get("NO₂", "")),
        remove_units(pollution_data.get("SO₂", "")),
        remove_units(pollution_data.get("O₃", "")),
        remove_units(pollution_data.get("AOD", "")),
        remove_units(pollution_data.get("Dust", "")),
        remove_units(pollution_data.get("UV Index", "")),
        remove_units(pollution_data.get("UV Index Clear Sky", "")),
        methane_csv,
        llm_name,
        llm_response,
        ollama_metrics.get("total_duration", ""),
        ollama_metrics.get("load_duration", ""),
        ollama_metrics.get("prompt_eval_count", ""),
        ollama_metrics.get("prompt_eval_duration", ""),
        ollama_metrics.get("eval_count", ""),
        ollama_metrics.get("eval_duration", ""),
        ollama_metrics.get("tokens_per_second", "")
    ]
    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(columns)
        writer.writerow(row)

# --- AQI and Map Constants ---
TILE_OPTIONS = [
    ("OpenStreetMap", "OpenStreetMap", None),
    ("CartoDB positron", "CartoDB positron", None),
]
CUSTOM_TILES = {}
AQI_BREAKPOINTS = {
    "pm2_5": [(0,30,0,50),(30,60,51,100),(60,90,101,200),(90,120,201,300),(120,250,301,400),(250,350,401,500)],
    "pm10":  [(0,50,0,50),(50,100,51,100),(100,250,101,200),(250,350,201,300),(350,430,301,400),(430,600,401,500)],
    "carbon_monoxide": [(0,1,0,50),(1,2,51,100),(2,10,101,200),(10,17,201,300),(17,34,301,400),(34,50,401,500)],
    "nitrogen_dioxide":[(0,40,0,50),(40,80,51,100),(80,180,101,200),(180,280,201,300),(280,400,301,400),(400,1000,401,500)],
    "sulphur_dioxide":[(0,40,0,50),(40,80,51,100),(80,380,101,200),(380,800,201,300),(800,1600,301,400),(1600,2000,401,500)],
    "ozone": [(0,50,0,50),(50,100,51,100),(100,168,101,200),(168,208,201,300),(208,748,301,400),(748,1000,401,500)],
}
AQI_BANDS = [
    (0,50,"Good","#009966"),
    (51,100,"Satisfactory","#ffde33"),
    (101,200,"Moderate","#ff9933"),
    (201,300,"Poor","#cc0033"),
    (301,400,"Very Poor","#660099"),
    (401,500,"Severe","#7e0023"),
]

# --- AQI Calculation Helpers ---
def sub_index(C, breakpoints):
    for C_low,C_high,I_low,I_high in breakpoints:
        if C_low <= C <= C_high:
            return ((I_high-I_low)/(C_high-C_low))*(C-C_low) + I_low
    if C < breakpoints[0][0]:
        return breakpoints[0][2]
    return breakpoints[-1][3]

def aqi_color(aqi: float):
    for low,high,label,color in AQI_BANDS:
        if low <= aqi <= high:
            return color,label
    return "#000000","Unknown"

# --- Get air quality HTML + methane value ---
def get_air_quality(lat, lon, location_name=None):
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "pm2_5","pm10","carbon_monoxide",
                "nitrogen_dioxide","sulphur_dioxide","ozone",
                "aerosol_optical_depth","dust",
                "uv_index","uv_index_clear_sky","methane"
            ]
        }
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        c = resp.json().get("current", {})

        pm25, pm10 = c.get("pm2_5",0), c.get("pm10",0)
        co_raw, no2_raw = c.get("carbon_monoxide",0), c.get("nitrogen_dioxide",0)
        so2_raw, o3_raw = c.get("sulphur_dioxide",0), c.get("ozone",0)
        co = co_raw/1000.0

        idx_pm25 = sub_index(pm25, AQI_BREAKPOINTS["pm2_5"])
        idx_pm10 = sub_index(pm10, AQI_BREAKPOINTS["pm10"])
        idx_co   = sub_index(co,   AQI_BREAKPOINTS["carbon_monoxide"])
        idx_no2  = sub_index(no2_raw, AQI_BREAKPOINTS["nitrogen_dioxide"])
        idx_so2  = sub_index(so2_raw, AQI_BREAKPOINTS["sulphur_dioxide"])
        idx_o3   = sub_index(o3_raw, AQI_BREAKPOINTS["ozone"])

        aqi = max(idx_pm25, idx_pm10, idx_co, idx_no2, idx_so2, idx_o3)
        color,label = aqi_color(aqi)

        aod  = c.get("aerosol_optical_depth",0)
        dust = c.get("dust",0)
        uv   = c.get("uv_index",0)
        uvcs = c.get("uv_index_clear_sky",0)
        ch4  = c.get("methane",0)

        legend_spans = "".join(
            f"<span style='display:inline-block;padding:.2em .6em;margin:.1em;"
            f"border-radius:4px;background:{col};color:#fff;font-size:.8em;'>{lbl}</span>"
            for _,_,lbl,col in AQI_BANDS
        )

        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        loc_disp = f"{location_name} " if location_name else ""

        html = f"""
        <div style="padding:1em;border:1px solid #ddd;border-radius:8px;
                    max-width:100%;margin-top:1em;">
          <h4 style="margin-bottom:.2em;">
            🌿 Air Quality Index of {loc_disp}({lat:.4f},{lon:.4f}) on {date_str}
          </h4>
          <div style="display:flex;align-items:center;">
            <div style="width:60px;height:60px;background:{color};
                        border-radius:50%;display:flex;align-items:center;
                        justify-content:center;font-size:1.25em;color:white;
                        margin-right:1em;">
              {int(aqi)}
            </div>
            <div><strong>{label}</strong></div>
          </div>
          <table style="width:100%;margin-top:.5em;font-size:.9em;">
            <tr><td>PM₂.₅:</td><td>{pm25} μg/m³ → {idx_pm25:.0f}</td></tr>
            <tr><td>PM₁₀:</td><td>{pm10} μg/m³ → {idx_pm10:.0f}</td></tr>
            <tr><td>CO:</td><td>{co:.3f} mg/m³ → {idx_co:.0f}</td></tr>
            <tr><td>NO₂:</td><td>{no2_raw} μg/m³ → {idx_no2:.0f}</td></tr>
            <tr><td>SO₂:</td><td>{so2_raw} μg/m³ → {idx_so2:.0f}</td></tr>
            <tr><td>O₃:</td><td>{o3_raw} μg/m³ → {idx_o3:.0f}</td></tr>
            <tr><td>AOD:</td><td>{aod}</td></tr>
            <tr><td>Dust:</td><td>{dust}</td></tr>
            <tr><td>UV Index:</td><td>{uv}</td></tr>
            <tr><td>UV Index Clear Sky:</td><td>{uvcs}</td></tr>
            <tr><td>Methane (CH₄):</td><td>{ch4} ppm</td></tr>
          </table>
          <div style="margin-top:1em;">
            <strong>Legend (AQI bands):</strong> {legend_spans}
          </div>
        </div>
        """
        return html, ch4
    except Exception as e:
        return f"<div style='color:red;'>Error fetching AQI data: {e}</div>", 0

# --- Extract pollution from HTML ---
def extract_pollution_from_html(html):
    data = {}
    for key in ["PM₂.₅","PM₁₀","CO","NO₂","SO₂","O₃","AOD","Dust","UV Index","UV Index Clear Sky","Methane (CH₄)"]:
        m = re.search(fr"{key}:</td><td>([^<]+)", html)
        if m:
            data[key] = m.group(1)
    return data

# --- Ollama LLM Integration ---
OLLAMA_IP = "192.168.31.235"
OLLAMA_PORT = "11434"
OLLAMA_BASE = f"http://{OLLAMA_IP}:{OLLAMA_PORT}"

def fetch_models():
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models",[])]
        if not models:
            models = ["granite3.1-moe:latest"]
        return gr.update(choices=models, value=models[0])
    except:
        return gr.update(choices=["granite3.1-moe:latest"], value="granite3.1-moe:latest")

def make_llm_prompt(pollution_data, location_name=None, user_question=None):
    prompt = (
        f"You are an expert and honest pollution analyzer and environmental health advisor specializing in Indian air quality and pollution data interpretation.\n\n"
        f"Below is the latest air quality data for the location {location_name or 'provided'}.\n"
        f"Whenever you answer, please..."
    )
    # build prompt with pollution_data
    for k,v in pollution_data.items():
        prompt += f"{k}: {v}\n"
    if user_question:
        prompt += f"User question: \"{user_question}\"\n"
    return prompt


def call_ollama_llm(prompt, model_name, chat_history=None):
    if chat_history:
        url = f"{OLLAMA_BASE}/api/chat"
        messages = chat_history + [{"role":"user","content":prompt}]
        data = {"model":model_name, "messages":messages, "stream":False, "think": False}
    else:
        url = f"{OLLAMA_BASE}/api/generate"
        data = {"model":model_name, "prompt":prompt, "stream":False, "think": False}
    resp = requests.post(url, json=data, timeout=120)
    resp.raise_for_status()
    res_json = resp.json()
    if 'message' in res_json:
        m = res_json['message']
        response = m.get('content',"")
    else:
        m = res_json
        response = m.get('response',"")
    metrics = {}
    for key in ["total_duration","load_duration","prompt_eval_count","prompt_eval_duration","eval_count","eval_duration"]:
        metrics[key] = m.get(key,"") or res_json.get(key,"")
    try:
        ec, ed = float(metrics["eval_count"]), float(metrics["eval_duration"])
        metrics["tokens_per_second"] = round(ec/ed*1e9,2) if ed>0 else ""
    except:
        metrics["tokens_per_second"] = ""
    return response, metrics

# --- LLM Advice: logs only on first Ask ---
def llm_advice(dt_html, model_name, chat_history, location_name):
    pollution_data = extract_pollution_from_html(dt_html)
    # extract lat/lon from dt_html
    m = re.search(r"\(([\d\.]+),([\d\.]+)\)", dt_html)
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
    else:
        lat, lon = None, None
    # fetch methane_raw anew
    methane_raw = 0
    if lat is not None:
        _, methane_raw = get_air_quality(lat, lon)
    # build & call LLM (use /api/generate for full metrics)
    prompt = make_llm_prompt(pollution_data, location_name)
    reply, ollama_metrics = call_ollama_llm(prompt, model_name, chat_history=None)
    # update chat state
    new_state = (chat_history or [])
    new_state.append({"role":"user","content":prompt})
    new_state.append({"role":"assistant","content":reply})
    # prepare methane_csv
    methane_csv = (
        remove_units(pollution_data.get("Methane (CH₄)",""))
        or remove_units(pollution_data.get("Methane",""))
        or remove_units(methane_raw)
        or ""
    )
    # log to CSV
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    append_llm_csv_row(
        timestamp=now_str,
        location=location_name or "",
        lat=lat or "",
        lon=lon or "",
        pollution_data=pollution_data,
        methane_csv=methane_csv,
        llm_name=model_name,
        llm_response=reply,
        ollama_metrics=ollama_metrics
    )
    return new_state

# --- User Chat (no logging) ---
def user_send(user_msg, model_name, chat_history):
    reply, _ = call_ollama_llm(user_msg, model_name, chat_history)
    new_state = (chat_history or [])
    new_state.append({"role":"user","content":user_msg})
    new_state.append({"role":"assistant","content":reply})
    return "", new_state

# --- Wrap for Gradio ---
def wrap_llm_advice(dt_html, model_name, chat_history, location_name, llm_locked):
    new_state = llm_advice(dt_html, model_name, chat_history, location_name)
    return new_state, gr.update(interactive=False), True

def wrap_user_send(user_msg, model_name, chat_history, llm_locked):
    msg, new_state = user_send(user_msg, model_name, chat_history)
    return msg, new_state, gr.update(interactive=False), True

# --- Location & Map functions ---
def is_within_india(lat, lon):
    return 6.0 <= lat <= 36.0 and 68.0 <= lon <= 98.0

def search_location_open_meteo(location_name):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name":location_name, "count":5, "language":"en",
              "format":"json","countryCode":"IN"}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        for res in resp.json().get("results", []):
            if res.get("country_code")=="IN":
                admin = ", ".join(filter(None,[res.get("admin1",""),res.get("admin2",""),res.get("admin3",""),res.get("admin4","")]))
                return {"lat":res["latitude"],"lon":res["longitude"],
                        "admin":admin,
                        "display":f"{res['name']} ({res['latitude']:.4f}, {res['longitude']:.4f})"}
    except:
        pass
    return None

def create_india_map(lat=None, lon=None, zoom_start=5, tiles_label="OpenStreetMap"):
    try:
        tile = next((t for t in TILE_OPTIONS if t[0]==tiles_label), None)
        if tile:
            tiles, attr = tile[1], tile[2]
        elif tiles_label in CUSTOM_TILES:
            tiles, attr = CUSTOM_TILES[tiles_label]
        else:
            tiles, attr = "OpenStreetMap", None
        args = {"location":[21.146633,79.088860], "zoom_start":zoom_start}
        args.update({"tiles":tiles})
        if attr: args.update({"attr":attr})
        m = folium.Map(**args)
        if lat and lon and is_within_india(lat, lon):
            folium.Marker([lat,lon], tooltip="Location",
                          popup=f"Lat: {lat:.4f}, Lon: {lon:.4f}",
                          icon=folium.Icon(color="blue",icon="info-sign")).add_to(m)
        return f"<div style='overflow:hidden;border-radius:18px;min-height:520px;max-width:100%;box-shadow:0 4px 18px #8882'>{m._repr_html_()}</div>"
    except Exception as e:
        return f"<div style='color:red;padding:1em;'>Error generating map: {e}</div>"

# --- Handlers for search & manual update ---
def search_and_set_location(name, zoom, tiles):
    if not name or len(name.strip())<3:
        return (gr.update(value=None),gr.update(value=None),
                "❌ Enter ≥3 chars", create_india_map(None,None,zoom,tiles), "",
                [], gr.update(interactive=True), False)
    r = search_location_open_meteo(name.strip())
    if not r:
        return (gr.update(value=None),gr.update(value=None),
                "❌ Not found/India", create_india_map(None,None,zoom,tiles), "",
                [], gr.update(interactive=True), False)
    lat, lon = r["lat"], r["lon"]
    msg = f"✅ <b>Found:</b> {r['display']}<br><i>{r['admin']}</i>"
    map_html = create_india_map(lat,lon,zoom,tiles)
    dt_html, _ = get_air_quality(lat, lon, r.get("display"))
    return (
        gr.update(value=lat), gr.update(value=lon),
        msg, map_html, dt_html,
        [],  # reset chat
        gr.update(interactive=True),
        False
    )

def manual_update(lat, lon, zoom, tiles):
    if lat is not None and lon is not None and is_within_india(lat, lon):
        msg = f"✅ Marker at ({lat:.4f},{lon:.4f})"
        map_html = create_india_map(lat,lon,zoom,tiles)
        dt_html, _ = get_air_quality(lat, lon)
    else:
        msg, dt_html = "ℹ️ Enter valid India coords or search", ""
        map_html = create_india_map(lat,lon,zoom,tiles)
    return (
        lat, lon, msg, map_html, dt_html,
        [], gr.update(interactive=True), False
    )

# --- Build UI ---
def build_ui():
    desc = """
    <div style="padding:18px 0 22px 0; text-align:center;">
      <span style="display:block;font-size:2.1em;font-weight:700;color:#245668;">
        India Air Quality Explorer With LLM Advice
      </span>
    </div>
    """
    with gr.Blocks(css=".gradio-container{background:#f9fafb;}") as demo:
        gr.HTML(desc)
        with gr.Row(): sb = gr.Textbox(label="Search Location", placeholder="E.g., Puri")
        with gr.Row(): la = gr.Number(label="Latitude", info="6–36") ; lo = gr.Number(label="Longitude", info="68–98")
        with gr.Row(): zm = gr.Slider(1,18,value=5,step=1,label="Zoom") ; tl = gr.Dropdown(choices=[t[0] for t in TILE_OPTIONS], value="OpenStreetMap", label="Tileset")
        msg = gr.HTML()
        mp  = gr.HTML(label="Map")
        dt  = gr.HTML(label="AQI & Data")

        model_dropdown = gr.Dropdown(choices=[], label="Choose LLM Model", interactive=True)
        demo.load(fetch_models, None, model_dropdown)
        
        

        submit_btn = gr.Button("Ask LLM for Pollution Analysis")
        chatbot   = gr.Chatbot([], label="Air Pollution LLM Chatbot", type="messages")
        user_msg  = gr.Textbox(label="Your message to LLM", placeholder="Ask follow-up question…")
        send_btn  = gr.Button("Send")

        llm_locked = gr.State(False)

        sb.submit(search_and_set_location, [sb,zm,tl], [la,lo,msg,mp,dt,chatbot,model_dropdown,llm_locked])
        for inp in (la,lo,zm,tl):
            inp.change(manual_update, [la,lo,zm,tl], [la,lo,msg,mp,dt,chatbot,model_dropdown,llm_locked])
        demo.load(lambda z,t: manual_update(None,None,z,t), [zm,tl], [la,lo,msg,mp,dt,chatbot,model_dropdown,llm_locked])

        submit_btn.click(wrap_llm_advice,
                         inputs=[dt, model_dropdown, chatbot, sb, llm_locked],
                         outputs=[chatbot, model_dropdown, llm_locked])

        send_btn.click(wrap_user_send,
                       inputs=[user_msg, model_dropdown, chatbot, llm_locked],
                       outputs=[user_msg, chatbot, model_dropdown, llm_locked])
    return demo

if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7860)
