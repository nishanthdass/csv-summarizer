import React, { createContext, useState, useContext, useEffect } from "react";
import { useChatWebSocket } from "./useChatWebsocket";

const SessionContext = createContext<{
  session: any;
  setSession: React.Dispatch<React.SetStateAction<any>>;
} | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState(null);
  const { reconnect, isConnected } = useChatWebSocket();

  useEffect(() => {
    if (!session){
        fetch("http://localhost:8000/get-session", {
            credentials: "include",
          })
            .then((response) => {
              if (response.status === 404) {
                
                console.log("No session found, creating new session...");
                return fetch("http://localhost:8000/set-session", {
                  credentials: "include",
                });
              }

              return response;
            })
            .then((response) => response.json())
            .then((data) => {
              console.log("Session found!")
              setSession(data);
              if (!isConnected) {
                console.log("Reconnecting WebSocket after session is formed...");
                reconnect();
              }
            })
            .catch((error) => console.error("Error checking or setting session:", error));
    }
  }, []);


  return (
    <SessionContext.Provider value={{ session, setSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
