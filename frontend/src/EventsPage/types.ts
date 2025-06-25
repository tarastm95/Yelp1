// src/types.ts

export interface PayloadUpdate {
  event_type: string;
  lead_id: string;
  event_content?: {
    text?: string;
    fallback_text?: string;
  };
  // If other fields are needed (cursor, user_type, etc.), add them here:
  [key: string]: any;
}

export interface EventItem {
  id: number | string;
  created_at: string;
  payload: {
    data: {
      updates: PayloadUpdate[];
    };
  };
}

export interface LeadDetail {
  lead_id: string;
  business_id: string;
  conversation_id: string;
  temporary_email_address?: string;
  temporary_email_address_expiry?: string;
  time_created: string;
  last_event_time?: string;
  user_display_name?: string;
  project?: {
    survey_answers?: Array<{
      question_text: string;
      answer_text: string[];
    }>;
    location?: Record<string, any>;
    additional_info?: string;
    availability?: {
      status: string;
      dates?: string[];
    };
    job_names?: string[];
    attachments?: Array<{
      id: string;
      url: string;
      resource_name: string;
      [key: string]: any;
    }>;
    [key: string]: any;
  };
  created_at?: string;
  updated_at?: string;
  // Add other fields here if needed
}

export interface ProcessedLead {
  lead_id: string;
  business_id: string;
  processed_at: string;
}

export interface LeadEvent {
  event_id: string;
  lead_id: string;
  event_type: string;
  user_type: string;
  user_id: string;
  user_display_name?: string;
  text?: string;
  cursor?: string;
  time_created: string;
  raw: any;
  created_at: string;
  updated_at: string;
}
