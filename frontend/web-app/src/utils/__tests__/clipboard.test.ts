import { copyToClipboard } from '../clipboard';

describe('copyToClipboard', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('uses navigator.clipboard.writeText when available', async () => {
    const writeTextMock = jest.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    Object.defineProperty(window, 'isSecureContext', {
      value: true,
      writable: true,
    });

    const result = await copyToClipboard('test text');

    expect(result).toBe(true);
    expect(writeTextMock).toHaveBeenCalledWith('test text');
  });

  test('uses fallback execCommand when clipboard API not available', async () => {
    // Mock missing clipboard API
    Object.assign(navigator, {
      clipboard: undefined,
    });

    // Mock document.execCommand
    const execCommandMock = jest.fn().mockReturnValue(true);
    document.execCommand = execCommandMock;

    // Mock document methods
    const appendChildSpy = jest.spyOn(document.body, 'appendChild');
    const removeChildSpy = jest.spyOn(document.body, 'removeChild');

    const result = await copyToClipboard('test text');

    expect(result).toBe(true);
    expect(execCommandMock).toHaveBeenCalledWith('copy');
    expect(appendChildSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
  });

  test('returns true on successful copy', async () => {
    const writeTextMock = jest.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    Object.defineProperty(window, 'isSecureContext', {
      value: true,
      writable: true,
    });

    const result = await copyToClipboard('success');

    expect(result).toBe(true);
  });

  test('returns false on clipboard API failure', async () => {
    const writeTextMock = jest.fn().mockRejectedValue(new Error('Permission denied'));
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    Object.defineProperty(window, 'isSecureContext', {
      value: true,
      writable: true,
    });

    const result = await copyToClipboard('fail text');

    expect(result).toBe(false);
  });

  test('returns false when execCommand fails', async () => {
    Object.assign(navigator, {
      clipboard: undefined,
    });

    const execCommandMock = jest.fn().mockReturnValue(false);
    document.execCommand = execCommandMock;

    jest.spyOn(document.body, 'appendChild').mockImplementation(() => null as any);
    jest.spyOn(document.body, 'removeChild').mockImplementation(() => null as any);

    const result = await copyToClipboard('fail text');

    expect(result).toBe(false);
  });

  test('creates textarea with correct properties in fallback', async () => {
    Object.assign(navigator, {
      clipboard: undefined,
    });

    document.execCommand = jest.fn().mockReturnValue(true);

    const createElementSpy = jest.spyOn(document, 'createElement');
    const appendChildSpy = jest.spyOn(document.body, 'appendChild');

    await copyToClipboard('test content');

    expect(createElementSpy).toHaveBeenCalledWith('textarea');

    // Check that textarea was appended
    expect(appendChildSpy).toHaveBeenCalled();
    const textarea = appendChildSpy.mock.calls[0][0] as HTMLTextAreaElement;

    expect(textarea.value).toBe('test content');
    expect(textarea.style.position).toBe('fixed');
    expect(textarea.style.left).toBe('-999999px');
  });

  test('handles permission errors gracefully', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    const writeTextMock = jest.fn().mockRejectedValue(new Error('Permission denied'));
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    Object.defineProperty(window, 'isSecureContext', {
      value: true,
      writable: true,
    });

    const result = await copyToClipboard('error text');

    expect(result).toBe(false);
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Failed to copy to clipboard:',
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
  });
});
