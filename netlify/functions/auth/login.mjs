import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    // Solo permitir POST
    if (event.httpMethod !== 'POST') {
        return { 
            statusCode: 405, 
            body: JSON.stringify({ success: false, error: 'Method not allowed' })
        };
    }

    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { username, password } = JSON.parse(event.body);
        
        console.log('Login attempt:', username); // Para debug
        
        // Buscar usuario
        const usuarios = await sql`
            SELECT id, username, nombre_completo, rol 
            FROM usuarios 
            WHERE username = ${username} AND activo = true
        `;
        
        console.log('Usuario encontrado:', usuarios); // Para debug
        
        if (usuarios.length === 0) {
            return {
                statusCode: 401,
                body: JSON.stringify({ 
                    success: false, 
                    error: 'Usuario no encontrado' 
                })
            };
        }
        
        // Por ahora aceptamos cualquier contraseña para pruebas
        // En producción deberías verificar la contraseña
        
        // Actualizar último acceso
        await sql`
            UPDATE usuarios 
            SET ultimo_acceso = CURRENT_TIMESTAMP 
            WHERE id = ${usuarios[0].id}
        `;
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                success: true,
                user: usuarios[0]
            })
        };
        
    } catch (error) {
        console.error('Login error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ 
                success: false, 
                error: error.message 
            })
        };
    }
}