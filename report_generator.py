import pandas as pd
from typing import List, Dict, Any
import html
import re

def clean_html(raw_html):
    """
    Removes HTML tags and unescapes characters for a cleaner text representation.
    """
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return html.unescape(cleantext)

def generate_report(tickets: List[Dict[str, Any]], filename: str = "freshdesk_report.xlsx"):
    """
    Converts a list of ticket objects (with nested conversations) into a flattened Excel file.
    """
    processed_data = []

    for ticket in tickets:
        ticket_id = ticket.get('id')
        subject = ticket.get('subject')
        
        # 'description' is the initial message (usually)
        description_html = ticket.get('description_text') or ticket.get('description') or ""
        initial_message = clean_html(description_html)
        
        # Process conversations (replies/notes)
        conversations = ticket.get('conversations', [])
        conversation_text = ""
        
        # Sort by creation date if needed, but usually api returns in order
        # Let's format the conversation history cleanly
        full_thread = [f"--- ORIGINAL MESSAGE [{ticket.get('created_at')}] ---\n{initial_message}\n"]
        
        for conv in conversations:
            c_type = "REPLY" if not conv.get('private') else "NOTE"
            c_from = conv.get('user_id') # Ideally we map this to a name if we had the user map, but ID is fallback
            c_body = clean_html(conv.get('body') or conv.get('body_text') or "")
            c_time = conv.get('created_at')
            
            entry = f"\n--- {c_type} from {c_from} at {c_time} ---\n{c_body}\n"
            full_thread.append(entry)
            
        final_thread_text = "\n".join(full_thread)
            
        # Add AI analysis if present
        ai_relevant = ticket.get('ai_relevant', 'N/A')
        ai_summary = ticket.get('ai_summary', '')
        
        processed_data.append({
            "Ticket ID": ticket_id,
            "Subject": subject,
            "Status": ticket.get('status'),
            "Priority": ticket.get('priority'),
            "Agent ID": ticket.get('responder_id'),
            "Created At": ticket.get('created_at'),
            "AI Relevance": ai_relevant,
            "AI Summary": ai_summary,
            "Full Conversation": final_thread_text
        })
        
    df = pd.DataFrame(processed_data)
    
    # Save to Excel
    print(f"Saving report with {len(df)} records to {filename}...")
    df.to_excel(filename, index=False)
    print("Done.")
