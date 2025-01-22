import React, { createContext, useState, useContext, useEffect, Dispatch } from "react";

const SessionContext = createContext<{
  session: any;
  setSession: React.Dispatch<React.SetStateAction<any>>;
} | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<any>(null); 
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session){
      console.log("Checking or setting session...");
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
              setSession(data);
            })
            .catch((error) => console.error("Error checking or setting session:", error))
            .finally(() => setLoading(false));
    }
  }, []);

  if (loading) {
    return <div>Loading...</div>; // Replace with your desired loading indicator
  }


  return (
    <SessionContext.Provider value={{ session, setSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
