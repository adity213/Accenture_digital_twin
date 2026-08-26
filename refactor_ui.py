import re

def update_css():
    with open('frontend/css/style.css', 'r', encoding='utf-8') as f:
        css = f.read()

    # 1. Update font imports
    old_fonts = "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700;800&display=swap');"
    new_fonts = "@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700;800&display=swap');"
    css = css.replace(old_fonts, new_fonts)

    # 2. Update :root variables
    root_old = """:root {
  --bg-page: #f1f5f9;
  --bg-gradient: radial-gradient(120% 120% at 50% 0%, #ffffff 0%, #f8fafc 50%, #e2e8f0 100%);
  
  --surface-panel: #ffffff;
  --surface-panel-raised: #f8fafc;
  --surface-panel-subtle: #f1f5f9;
  
  --border-subtle: #cbd5e1;
  --border-strong: #94a3b8;
  
  --text-primary: #0f172a;       /* Deep Slate / Black */
  --text-secondary: #334155;     /* Slate */
  --text-muted: #64748b;         /* Muted Slate */
  --text-inverse: #ffffff;

  --status-nominal: #15803d;     /* Deep Emerald */
  --status-nominal-bg: #dcfce7;
  --status-warning: #b45309;     /* Deep Amber */
  --status-warning-bg: #fef3c7;
  --status-critical: #b91c1c;    /* Deep Crimson */
  --status-critical-bg: #fee2e2;

  --brand-blue: #0057ff;
  --brand-blue-hover: #0046d6;
  --brand-blue-soft: rgba(0, 87, 255, 0.08);
  --accent-signal: #d97706;

  --font-brand: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.06), 0 8px 24px -4px rgba(15, 23, 42, 0.08);
  --shadow-node: 0 2px 8px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(15, 23, 42, 0.05);
  --shadow-node-active: 0 0 0 2px var(--brand-blue), 0 12px 28px -4px rgba(0, 87, 255, 0.25);"""

    root_new = """:root {
  --bg-page: #0A0D10;
  --bg-gradient: #0A0D10;
  
  --surface-panel: #12161B;
  --surface-panel-raised: #1A2027;
  --surface-panel-subtle: #0A0D10;
  
  --border-subtle: #1E3A4C;
  --border-strong: #5C6B78;
  
  --text-primary: #E7EDF2;
  --text-secondary: #8A97A3;
  --text-muted: #5C6B78;
  --text-inverse: #0A0D10;

  --status-nominal: #2ECC71;
  --status-nominal-bg: rgba(46, 204, 113, 0.1);
  --status-warning: #F5A623;
  --status-warning-bg: rgba(245, 166, 35, 0.1);
  --status-critical: #FF4D4F;
  --status-critical-bg: rgba(255, 77, 79, 0.1);
  --status-offline: #3A4148;

  --brand-blue: #FFB020;
  --brand-blue-hover: #E59D1C;
  --brand-blue-soft: rgba(255, 176, 32, 0.1);
  --accent-signal: #FFB020;
  --accent-weld: #66D9EF;

  --font-brand: 'Barlow Condensed', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --shadow-card: 0 4px 12px rgba(0, 0, 0, 0.5);
  --shadow-node: 0 2px 8px rgba(0, 0, 0, 0.4);
  --shadow-node-active: 0 0 0 2px var(--brand-blue), 0 0 20px rgba(255, 176, 32, 0.2);"""

    css = css.replace(root_old, root_new)
    
    # Update grid background (blueprint style)
    css = re.sub(r'\.blueprint-grid-bg\s*\{[^}]*\}', 
                 '.blueprint-grid-bg {\n  background-color: var(--bg-page);\n  background-image: \n    linear-gradient(to right, rgba(30, 58, 76, 0.15) 1px, transparent 1px),\n    linear-gradient(to bottom, rgba(30, 58, 76, 0.15) 1px, transparent 1px);\n  background-size: 24px 24px;\n}', css)

    # 3. Replace hardcoded colors in CSS body
    css = css.replace('background: #ffffff;', 'background: var(--surface-panel);')
    css = css.replace('background: #f8fafc;', 'background: var(--surface-panel-raised);')
    css = css.replace('background: #f1f5f9;', 'background: var(--surface-panel-subtle);')
    css = css.replace('color: #ffffff;', 'color: var(--text-primary);')
    css = css.replace('color: #0f172a;', 'color: var(--text-primary);')
    css = css.replace('background: #0f172a;', 'background: var(--surface-panel-raised);')
    css = css.replace('border-color: #0f172a;', 'border-color: var(--surface-panel-raised);')
    
    # Specific rail/zone changes
    css = css.replace('background: #f0f9ff;', 'background: rgba(2, 132, 199, 0.1);')
    css = css.replace('background: #f5f7ff;', 'background: rgba(99, 102, 241, 0.1);')
    css = css.replace('background: #f0fdf4;', 'background: rgba(16, 185, 129, 0.1);')
    
    css = css.replace('fill="#ffffff"', 'fill="var(--surface-panel)"')
    css = css.replace('fill="#0057ff"', 'fill="var(--brand-blue)"')
    css = css.replace('stroke="#0057ff"', 'stroke="var(--brand-blue)"')
    
    with open('frontend/css/style.css', 'w', encoding='utf-8') as f:
        f.write(css)

def update_js():
    with open('frontend/js/twin_scene.js', 'r', encoding='utf-8') as f:
        js = f.read()
    
    # Replace hardcoded colors in getMachineGlyph
    js = js.replace('#f1f5f9', 'var(--surface-panel-raised)')
    js = js.replace('#94a3b8', 'var(--border-strong)')
    js = js.replace('#0f172a', 'var(--steel)')
    js = js.replace('#0057ff', 'var(--brand-blue)')
    js = js.replace('#f59e0b', 'var(--status-warning)')
    js = js.replace('#0284c7', 'var(--accent-weld)')
    js = js.replace('#334155', 'var(--steel)')
    js = js.replace('#fffbeb', 'var(--status-warning-bg)')
    js = js.replace('#d97706', 'var(--status-warning)')
    js = js.replace('#f0f9ff', 'var(--surface-panel-raised)')
    js = js.replace('#10b981', 'var(--status-nominal)')
    js = js.replace('#ffffff', 'var(--bg-panel)')
    js = js.replace('#fef3c7', 'var(--status-warning-bg)')
    js = js.replace('#15803d', 'var(--status-nominal)')
    js = js.replace('#f8fafc', 'var(--surface-panel-raised)')

    # Add confidence opacity logic in updateTelemetry
    confidence_logic = """
      // CONFIDENCE OPACITY
      if (st.twin_confidence !== undefined) {
          node.style.opacity = Math.max(0.3, st.twin_confidence);
          node.style.filter = `saturate(${Math.max(30, st.twin_confidence * 100)}%)`;
      }
"""
    js = js.replace('if (ctEl) ctEl.innerText', confidence_logic + '      if (ctEl) ctEl.innerText')
    
    # Ensure car silhouettes stand out on dark bg
    js = js.replace('fill="#0057ff"', 'fill="var(--accent-signal)"')
    js = js.replace('stroke="#0046d6"', 'stroke="var(--accent-signal)"')
    
    with open('frontend/js/twin_scene.js', 'w', encoding='utf-8') as f:
        f.write(js)

def update_html():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
        
    html = html.replace('TwinSphere Crisp White Glassmorphism Design System', 'TwinSphere Dark Industrial Control Room')
    html = html.replace('fill="#0057ff"', 'fill="var(--brand-blue)"')
    html = html.replace('color: #0f172a;', 'color: var(--text-primary);')
    html = html.replace('background: #0f172a;', 'background: var(--surface-panel-raised);')
    
    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(html)

update_css()
update_js()
update_html()
