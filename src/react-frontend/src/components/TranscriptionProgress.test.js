import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import TranscriptionProgress from './TranscriptionProgress';

// Mock WebSocket
class MockWebSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;

    // Store instance for test access
    MockWebSocket.instances.push(this);

    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) {
        this.onopen({});
      }
    }, 10);
  }

  send(data) {
    // Mock send - just store the data
    this.lastSentData = data;
  }

  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) {
      this.onclose({});
    }
  }

  // Helper method to simulate receiving a message
  _simulateMessage(message) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(message) });
    }
  }

  // Helper method to simulate an error
  _simulateError() {
    if (this.onerror) {
      this.onerror({});
    }
  }

  // Static method to get all instances
  static getInstances() {
    return MockWebSocket.instances;
  }

  // Static method to clear instances
  static clearInstances() {
    MockWebSocket.instances = [];
  }
}

global.WebSocket = MockWebSocket;

describe('TranscriptionProgress Component', () => {
  beforeEach(() => {
    MockWebSocket.clearInstances();
  });

  test('renders loading state when job ID is provided', () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    render(
      <TranscriptionProgress
        jobId="test-job-123"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Should show progress bar
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toBeInTheDocument();

    // Should show initial status
    expect(screen.getByText(/initializing/i)).toBeInTheDocument();
  });

  test('connects to WebSocket with correct job ID', () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    render(
      <TranscriptionProgress
        jobId="test-job-456"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Get the WebSocket instance
    const instances = MockWebSocket.getInstances();
    expect(instances.length).toBeGreaterThan(0);

    // Check if URL contains job ID
    expect(instances[instances.length - 1].url).toContain('test-job-456');
  });

  test('updates progress when receiving progress messages', async () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    render(
      <TranscriptionProgress
        jobId="test-job-789"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText(/initializing/i)).toBeInTheDocument();
    });

    // Simulate progress message
    await act(async () => {
      const instances = MockWebSocket.getInstances();
      const wsInstance = instances[instances.length - 1];
      if (wsInstance && wsInstance._simulateMessage) {
        wsInstance._simulateMessage({
          status: 'processing',
          progress: 45,
          time_remaining: 30,
          cost_estimate: 0.02
        });
      }
    });

    // Check if progress is updated
    await waitFor(() => {
      expect(screen.getByText('45%', { exact: false })).toBeInTheDocument();
      expect(screen.getByText('Status:', { exact: false })).toBeInTheDocument();
    });
  });

  test('calls onComplete when status is completed', async () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    const result = {
      text: 'This is the transcription result',
      segments: []
    };

    render(
      <TranscriptionProgress
        jobId="test-job-complete"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText(/initializing/i)).toBeInTheDocument();
    });

    // Simulate completion message
    await act(async () => {
      const instances = MockWebSocket.getInstances();
      const wsInstance = instances[instances.length - 1];
      if (wsInstance && wsInstance._simulateMessage) {
        wsInstance._simulateMessage({
          status: 'completed',
          result: result
        });
      }
    });

    // Check if onComplete was called with result
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith(result);
    });
  });

  test('calls onError when status is failed', async () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    const errorMessage = 'Transcription failed due to error';

    render(
      <TranscriptionProgress
        jobId="test-job-failed"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText(/initializing/i)).toBeInTheDocument();
    });

    // Simulate failure message
    await act(async () => {
      const instances = MockWebSocket.getInstances();
      const wsInstance = instances[instances.length - 1];
      if (wsInstance && wsInstance._simulateMessage) {
        wsInstance._simulateMessage({
          status: 'failed',
          error: errorMessage
        });
      }
    });

    // Check if onError was called
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(errorMessage);
    });
  });

  test('cleans up WebSocket on unmount', () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    const { unmount } = render(
      <TranscriptionProgress
        jobId="test-job-unmount"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Get WebSocket instance
    const instances = MockWebSocket.getInstances();
    const wsInstance = instances[instances.length - 1];

    // Unmount component
    unmount();

    // WebSocket should be closed
    expect(wsInstance.readyState).toBe(3); // CLOSED
  });

  test('displays time remaining estimate', async () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    render(
      <TranscriptionProgress
        jobId="test-job-time"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText(/initializing/i)).toBeInTheDocument();
    });

    // Simulate progress message with time remaining
    await act(async () => {
      const instances = MockWebSocket.getInstances();
      const wsInstance = instances[instances.length - 1];
      if (wsInstance && wsInstance._simulateMessage) {
        wsInstance._simulateMessage({
          status: 'processing',
          progress: 60,
          time_remaining: 45,
          cost_estimate: 0.03
        });
      }
    });

    // Check if time remaining is displayed
    await waitFor(() => {
      expect(screen.getByText(/45 sec/i)).toBeInTheDocument();
    });
  });

  test('displays cost estimate', async () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    render(
      <TranscriptionProgress
        jobId="test-job-cost"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText(/initializing/i)).toBeInTheDocument();
    });

    // Simulate progress message with cost estimate
    await act(async () => {
      const instances = MockWebSocket.getInstances();
      const wsInstance = instances[instances.length - 1];
      if (wsInstance && wsInstance._simulateMessage) {
        wsInstance._simulateMessage({
          status: 'processing',
          progress: 75,
          time_remaining: 20,
          cost_estimate: 0.05
        });
      }
    });

    // Check if cost estimate is displayed
    await waitFor(() => {
      expect(screen.getByText(/\$0.0500/i)).toBeInTheDocument();
    });
  });

  test('handles WebSocket connection errors gracefully', async () => {
    const onComplete = jest.fn();
    const onError = jest.fn();

    render(
      <TranscriptionProgress
        jobId="test-job-error"
        onComplete={onComplete}
        onError={onError}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText(/initializing/i)).toBeInTheDocument();
    });

    // Simulate WebSocket error
    await act(async () => {
      const instances = MockWebSocket.getInstances();
      const wsInstance = instances[instances.length - 1];
      if (wsInstance && wsInstance._simulateError) {
        wsInstance._simulateError();
      }
    });

    // Check if error callback was called
    await waitFor(() => {
      expect(onError).toHaveBeenCalled();
    });
  });
});
