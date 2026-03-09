import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        // Probar conexión
        const result = await sql`SELECT version()`;
        
        return {
            statusCode: 200,
            body: JSON.stringify({
                success: true,
                message: "✅ Conectado a PostgreSQL",
                version: result[0].version
            })
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({
                success: false,
                error: error.message
            })
        };
    }
}