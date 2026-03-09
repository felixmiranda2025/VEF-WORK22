import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const [clientes, proyectos, cotizaciones, ordenes] = await Promise.all([
            sql`SELECT COUNT(*) as count FROM clientes`,
            sql`SELECT COUNT(*) as count FROM proyectos WHERE estatus = 'activo'`,
            sql`SELECT COUNT(*) as count FROM cotizaciones WHERE estatus = 'pendiente'`,
            sql`SELECT COUNT(*) as count FROM ordenes_compra WHERE estatus = 'pendiente'`
        ]);
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                stats: {
                    clientes: clientes[0].count,
                    proyectos_activos: proyectos[0].count,
                    cotizaciones_pendientes: cotizaciones[0].count,
                    ordenes_pendientes: ordenes[0].count
                }
            })
        };
        
    } catch (error) {
        console.error('Error obteniendo estadísticas:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}