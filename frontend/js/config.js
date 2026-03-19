/**
 * Configuration for Exam Attendance System
 */
const CONFIG = {
    // Current environment - set to 'prod' for Cloudflare deployment
    ENV: 'dev',

    // API base URL
    API_BASE: {
        dev: `${window.location.protocol}//${window.location.hostname}:8000/api`,
        prod: '/api' 
    },

    getApiBase() {
        return this.API_BASE[this.ENV];
    }
};

window.APP_CONFIG = CONFIG;
