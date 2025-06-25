// src/types.ts

// For updates inside the payload
export interface PayloadUpdate {
  event_type: string;
  lead_id: string;
}

// Initial Event from /events
export interface EventItem {
  id: number | string;
  created_at: string;
  payload?: {
    data?: {
      updates?: PayloadUpdate[];
      [key: string]: any;
    };
    [key: string]: any;
  };
}

// Detailed events in EventDetail
export interface Attachment {
  id: string;
  mime_type: string;
  url: string;
  resource_name: string | null;
}
export interface EventContent {
  fallback_text: string;
  text?: string;
  attachments?: Attachment[];
}
export interface DetailedEvent {
  id: string;
  cursor: string;
  time_created: string;
  event_type: string;
  user_type: string;
  user_id: string;
  user_display_name: string;
  event_content: EventContent;
}

// For ScheduledMessagesSection
export interface ScheduledMessage {
  id: number;
  content: string;
  interval_minutes: number;
  next_run: string;
  active: boolean;
}
export interface MessageHistory {
  id: number;
  executed_at: string;
  status: string;
  error?: string;
}

// For LeadDetail (full response from /api/yelp/leads/:id)
export interface SurveyAnswer {
  question_text: string;
  answer_text: string[];
}
export interface LocationInfo {
  postal_code?: string;
  [key: string]: any;
}
export interface Availability {
  status: string;
  dates: string[];
}
export interface ProjectInfo {
  survey_answers?: SurveyAnswer[];
  location?: LocationInfo;
  additional_info?: string;
  availability?: Availability;
  job_names?: string[];
  attachments?: Attachment[];
  [key: string]: any;
}
export interface LeadDetail {
  business_id: string;
  id: string;
  conversation_id: string;
  temporary_email_address?: string;
  temporary_email_address_expiry?: string;
  time_created: string;
  last_event_time: string;
  user: {
    display_name: string;
    [key: string]: any;
  };
  project?: ProjectInfo;
  [key: string]: any;
}

// Props for the scheduled messages section with placeholders for name/jobs
export interface ScheduledSectionProps {
  leadId: string;
  displayName: string;
  jobNames: string[];
  scheduled: ScheduledMessage[];
  history?: MessageHistory[]; 
  onUpdate: () => void;
}

export interface InstantSectionProps {
  leadId: string;
  displayName: string;
  jobNames: string[];
  onSent: () => void;
}
