import { createClient } from '@supabase/supabase-js'
import type { Database } from '../types/supabase'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://nnmmhgnriisfsncphipd.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ubW1oZ25yaWlzZnNuY3BoaXBkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE3OTE2MzYsImV4cCI6MjA3NzM2NzYzNn0.aNFk9PwFF-vPAs9CJl6VtvXM0EC333uS32iBTD3-ylQ'

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey)

// Helper functions for common operations
export const auth = supabase.auth
export const db = supabase.from

// Type exports for convenience
export type { Database, Tables, TablesInsert, TablesUpdate } from '../types/supabase'
