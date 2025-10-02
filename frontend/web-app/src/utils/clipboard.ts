/**
 * Copies text to the clipboard using the modern Clipboard API with fallback
 * @param text The text to copy to clipboard
 * @returns Promise<boolean> - true if successful, false otherwise
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    // Modern Clipboard API (requires HTTPS or localhost)
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      // Fallback for older browsers or non-secure contexts
      const textArea = document.createElement('textarea');
      textArea.value = text;

      // Make the textarea invisible but functional
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      textArea.setAttribute('readonly', '');

      document.body.appendChild(textArea);

      // Select and copy the text
      textArea.select();
      textArea.setSelectionRange(0, text.length);

      const success = document.execCommand('copy');

      // Clean up
      document.body.removeChild(textArea);

      return success;
    }
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};
