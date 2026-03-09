import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const token = event.headers.authorization?.replace('Bearer ', '');
        
        if (!token) {
            return {
                statusCode: 401,
                body: JSON.stringify({ success: false, error: 'No token provided' })
            };
        }
        
        // Aquí deberías verificar el token JWT
        // Por ahora, solo verificamos que exista
        
        return {
            statusCode: 200,
            body: JSON.stringify({ success: true, valid: true })
        };
        
    } catch (error) {
        return {
            statusCode: 401,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}