import { useState, useEffect } from 'react';
import { User } from 'lucide-react';

export default function LoginScreen({ onLogin }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    try {
      const response = await fetch('http://localhost:8000/api/users/list');
      const data = await response.json();
      setUsers(data.users);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleUserSelect(user) {
    try {
      // Update last_active timestamp
      await fetch(`http://localhost:8000/api/users/${user.id}/select`, {
        method: 'POST'
      });
      
      // Store user in localStorage
      localStorage.setItem('currentUser', JSON.stringify(user));
      
      // Call onLogin callback
      onLogin(user);
    } catch (error) {
      console.error('Failed to select user:', error);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background-elevated to-background">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-100" />
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-200" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background-elevated to-background p-8">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-12 animate-fade-up">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-accent to-indigo-600 flex items-center justify-center shadow-accent-glow">
            <User className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold gradient-text mb-2">Welcome Back</h1>
          <p className="text-foreground-muted">Select your profile to continue</p>
        </div>

        {/* User Selection */}
        <div className="space-y-4">
          {users.map((user, idx) => (
            <button
              key={user.id}
              onClick={() => handleUserSelect(user)}
              className="w-full glass-card p-6 flex items-center gap-4 hover:scale-[1.02] transition-all duration-200 animate-fade-up"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              {/* Avatar */}
              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-accent to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-accent-glow">
                {user.profile_picture ? (
                  <img 
                    src={`/assets/profiles/${user.profile_picture}`} 
                    alt={user.username}
                    className="w-full h-full object-cover rounded-xl"
                  />
                ) : (
                  <User className="w-8 h-8 text-white" />
                )}
              </div>

              {/* User Info */}
              <div className="flex-1 text-left">
                <h3 className="text-xl font-semibold text-foreground mb-1">
                  {user.username}
                </h3>
                <p className="text-sm text-foreground-muted">
                  Last active: {new Date(user.last_active).toLocaleDateString()}
                </p>
              </div>

              {/* Arrow */}
              <div className="text-foreground-muted">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-foreground-subtle">
          <p>Click on a profile to login</p>
        </div>
      </div>
    </div>
  );
}
