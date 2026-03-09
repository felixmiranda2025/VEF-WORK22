import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    if (event.httpMethod !== 'PUT') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { id, nombre, email, telefono, direccion, rfc, contacto_nombre, contacto_telefono, notas } = JSON.parse(event.body);
        
        if (!id || !nombre) {
            return {
                statusCode: 400,
                body: JSON.stringify({ success: false, error: 'ID y nombre son requeridos' })
            };
        }
        
        const result = await sql`
            UPDATE clientes 
            SET 
                nombre = ${nombre},
                email = ${email || null},
                telefono = ${telefono || null},
                direccion = ${direccion || null},
                rfc = ${rfc || null},
                contacto_nombre = ${contacto_nombre || null},
                contacto_telefono = ${contacto_telefono || null},
                notas = ${notas || null}
            WHERE id = ${id}
            RETURNING *
        `;
        
        if (result.length === 0) {
            return {
                statusCode: 404,
                body: JSON.stringify({ success: false, error: 'Cliente no encontrado' })
            };
        }
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                cliente: result[0]
            })
        };
        
    } catch (error) {
        console.error('Error actualizando cliente:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}