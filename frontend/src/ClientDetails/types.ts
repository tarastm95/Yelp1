// src/types.ts

// API response: question options
export interface SurveyAnswer {
  question_text: string;
  answer_text: string[];
}

// Project location
export interface LocationInfo {
  postal_code?: string;
  [key: string]: any;
}

// Availability
export interface Availability {
  status: string;
  dates: string[];
}

// Attachment (could be an image or other file)
export interface Attachment {
  id: string;
  mime_type: string;
  resource_name: string;
  url: string;
}

// Project data
export interface ProjectInfo {
  survey_answers?: SurveyAnswer[];
  location?: LocationInfo;
  additional_info?: string;
  availability?: Availability;
  job_names?: string[];
  attachments?: Attachment[];
  [key: string]: any;
}

// Full lead details
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
