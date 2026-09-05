/**
 * Format monetary amount in integer paise to INR string (e.g. 49900 -> ₹499.00).
 */
export const formatINR = (paise: number): string => {
  if (isNaN(paise) || paise === null || paise === undefined) return '₹0.00';
  const rupees = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rupees);
};

/**
 * Format ISO timestamp string into a human-readable date & time.
 * e.g., "2026-09-04T23:30:00Z" -> "Sep 4, 2026, 23:30"
 */
export const formatTimestamp = (timestamp?: string): string => {
  if (!timestamp) return 'N/A';
  try {
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return timestamp;
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return timestamp;
  }
};

/**
 * Format relative time (e.g., "2 minutes ago", "Today, 18:42")
 */
export const formatRelativeTime = (timestamp?: string): string => {
  if (!timestamp) return 'Just now';
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);

    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;

    return formatTimestamp(timestamp);
  } catch {
    return timestamp;
  }
};
