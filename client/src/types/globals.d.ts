// Global ambient type declarations for PK-Hub

interface Job {
  run_id: string;
  scraper: any;
  status: any;
  step: string;
  started_at: string;
  finished_at: string | null;
  bids_found: number;
  bids_processed: number;
  documents_downloaded: number;
  queue_position?: number;
  errors: number;
  warnings: number;
  log_seq?: number;
  [key: string]: any;
}

interface RideMetroAgency {
  name: string;
  url: string;
  agency_id?: string;
  status: string;
  skipped: boolean;
  opportunities: number;
  error?: string | null;
  note?: string | null;
}

interface BidResult {
  [key: string]: any;
}

