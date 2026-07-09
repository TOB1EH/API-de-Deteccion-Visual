import { createVuetify } from 'vuetify'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        dark: true,
        colors: {
          background: '#0F172A',
          surface: '#1E293B',
          primary: '#3B82F6',
          secondary: '#8B5CF6',
          accent: '#06B6D4',
          error: '#EF4444',
          info: '#3B82F6',
          success: '#22C55E',
          warning: '#F59E0B'
        }
      },
      light: {
        dark: false,
        colors: {
          background: '#F8FAFC',
          surface: '#FFFFFF',
          primary: '#2563EB',
          secondary: '#7C3AED',
          accent: '#0891B2',
          error: '#DC2626',
          info: '#2563EB',
          success: '#16A34A',
          warning: '#D97706'
        }
      }
    }
  },
  defaults: {
    VCard: {
      elevation: 0,
      class: 'border'
    },
    VBtn: {
      class: 'text-none'
    }
  }
})
