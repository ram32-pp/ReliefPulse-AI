'use client';

import { useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { WS_URL } from '@/lib/constants';

export const useWebSocket = (onMessage: (msg: any) => void) => {
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socket = io(WS_URL, {
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
      console.log('Connected to WebSocket server');
    });

    socket.on('message', (data) => {
      onMessage(data);
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, [onMessage]);

  const sendMessage = (event: string, data: any) => {
    socketRef.current?.emit(event, data);
  };

  return { sendMessage };
};
