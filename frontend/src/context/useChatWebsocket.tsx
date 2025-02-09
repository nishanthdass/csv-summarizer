import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useFetchDataDatabase } from "../hooks/fetch_hooks/useFetchDataDatabase";


interface MessageInstance {
  role: string;
  table_name: string;
  pdf_name: string;
  event: string;
  message: string;
  time?: string;
  answer_query?: string | null;
  viewing_query_label?: string | null;
}

interface ChatWebsocketContextValue {
  isConnected: boolean;
  sendMessage: (table_name: string, pdf_name: string, input: string) => void;
  input: MessageInstance[];
  messages: MessageInstance[];
  setMessages: React.Dispatch<React.SetStateAction<MessageInstance[]>>;
  reconnect: () => void;
  setIsChatOpen: React.Dispatch<React.SetStateAction<boolean>>
  isChatOpen: boolean
}

interface ChatWebsocketProviderProps {
  url: string;
  children: React.ReactNode;
}

const ChatWebsocketContext = createContext<ChatWebsocketContextValue | undefined>(undefined);

export const ChatWebsocketProvider: React.FC<ChatWebsocketProviderProps> = ({ url, children }) => {
  const [ isConnected, setIsConnected ] = useState(false);
  const [ isChatOpen, setIsChatOpen ] = useState(false);
  const [ messages, setMessages ] = useState<MessageInstance[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectSocketRef = useRef(true);

  const { fetchStartChat } = useFetchDataDatabase();


  const formatIncomingMessage = (data: any): MessageInstance => {
    const message = {
      role: String(data.role),
      table_name: String(data.table_name),
      pdf_name: String(data.pdf_name),
      event: String(data.event),
      message: String(data.message),
      time: data.time ? String(data.time) : "0",
      answer_query: convertStringNullToNull(data.answer_query),
      viewing_query_label: convertStringNullToNull(data.viewing_query_label),
    };
  
    console.log("Incoming message: ", message);
    return message;
  };
  
  const convertStringNullToNull = (value: any): any => {
    return value === "null" ? null : value;
  };
  

  const formatOutgoingMessage = (role: string, table_name: string, pdf_name: string, message: string, event: string): MessageInstance => ({
    role,
    table_name,
    pdf_name,
    event,
    message,
  });


  // Socket operations
  const connect = () => {
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      // console.log("WebSocket connected");
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const parsedData = JSON.parse(event.data);
        const message = formatIncomingMessage(parsedData);

        if (message.event === "on_chain_start") {
          addNewMessage(message);
        }

        if (message.event === "on_chat_model_stream") {
          buildOnLastMessage(message);
        }

        if (message.event === "on_chain_end") {
          finishLastMessage(message);
        }
        
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };
    

    socket.onclose = () => {
      // console.log("WebSocket disconnected");
      setIsConnected(false);

      if (reconnectSocketRef.current) {
        setTimeout(() => {
          // console.log("Reconnecting...");
          connect();
        }, 2000);
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      socket.close(); // optional
    };
  };

  // use effect to connect socket and set up reconnect logic
  useEffect(() => {
    reconnectSocketRef.current = true;
    connect();

    return () => {
      reconnectSocketRef.current = false;
      if (socketRef.current) {
        socketRef.current.close();
      }
    };

  }, [url]);

  useEffect(() => {
    if (isConnected && !isChatOpen) {
      fetchStartChat();
      setIsChatOpen(true);
    }
  }, [isConnected, isChatOpen]);


  // Seperated reconnect function for manual reconnection
  const reconnect = () => {
    if (socketRef.current) {
      socketRef.current.close();
    }
    connect();
  };


  const sendMessage = (table_name: string, pdf_name: string, input: string) => {
    const formattedUserMessage = formatOutgoingMessage("User", table_name, pdf_name, input, "request");
    
    addNewMessage(formattedUserMessage);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(formattedUserMessage));
    } else {
      console.error("WebSocket is not open. Cannot send message.");
    }
  };

  const addNewMessage = (message: MessageInstance) => {
    const newMessage = {
      ...message,
      time: message.time || "0",  // Set default time if missing
    };
  
    console.log("Adding new message:", newMessage);  // Debugging log
    setMessages((prevMessages) => [...prevMessages, newMessage]);
  };
  

  const buildOnLastMessage = (deltaMessage: MessageInstance) => {
    setMessages((prevMessages) => {
      if (prevMessages.length === 0) {
        console.warn("No messages to update.");
        return prevMessages;
      }
      const updatedMessages = [...prevMessages];
      const lastMessage = updatedMessages[updatedMessages.length - 1];
      updatedMessages[updatedMessages.length - 1] = {
        ...lastMessage,
        message: deltaMessage.message,
        time: deltaMessage.time
      };
  
      return updatedMessages;
    });
  };

  const finishLastMessage = (message: MessageInstance) => {
    setMessages((prevMessages) => {
      if (prevMessages.length === 0) {
        console.warn("No messages to update.");
        return prevMessages;
      }
      const updatedMessages = [...prevMessages];
      const lastMessage = updatedMessages[updatedMessages.length - 1];

      updatedMessages[updatedMessages.length - 1] = {
        ...lastMessage,
        message: message.message,
        time: message.time,
        answer_query: message.answer_query,
        viewing_query_label: message.viewing_query_label
      };
  
      return updatedMessages;
    });
  };

  

  return (
    <ChatWebsocketContext.Provider value={{ isConnected, sendMessage, input: messages, messages, setMessages, reconnect, setIsChatOpen, isChatOpen }}>
      {children}
    </ChatWebsocketContext.Provider>
  );
};

export const useChatWebSocket = () => {
  const context = useContext(ChatWebsocketContext);
  if (!context) {
    throw new Error("useChatWebSocket must be used within a ChatWebsocketProvider");
  }
  return context;
};
