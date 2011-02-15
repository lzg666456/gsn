package gsn;

import gsn.beans.DataField;
import gsn.beans.VSensorConfig;
import java.util.Iterator;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import org.apache.log4j.Logger;

public final class Mappings {
   
   private static final ConcurrentHashMap<String,VSensorConfig>              vsNameTOVSConfig               = new ConcurrentHashMap<String,VSensorConfig>( );
   
   private static final ConcurrentHashMap < String , VirtualSensorPool >             fileNameToVSInstance           = new ConcurrentHashMap < String , VirtualSensorPool >(  );
   
   private static final ConcurrentHashMap < String , TreeMap < String , Boolean >> vsNamesToOutputStructureFields = new ConcurrentHashMap < String , TreeMap < String , Boolean >>( );
   
   private static final transient Logger                                 logger                         = Logger.getLogger( Mappings.class );
   
   private static ContainerImpl                                              container                      = new ContainerImpl ( );
   
   public static boolean addVSensorInstance ( VirtualSensorPool sensorPool ) {
      try {
         if ( logger.isInfoEnabled( ) ) logger.info( ( new StringBuilder( "Testing the pool for :" ) ).append( sensorPool.getConfig( ).getName( ) ).toString( ) );
         sensorPool.returnVS( sensorPool.borrowVS( ) );
      } catch ( Exception e ) {
         logger.error( e.getMessage( ) , e );
         sensorPool.closePool( );
         logger.error( "GSN can't load the virtual sensor specified at " + sensorPool.getConfig( ).getFileName( ) + " because the initialization of the virtual sensor failed (see above exception)." );
         logger.error( "Please fix the following error" );
         return false;
      }
      TreeMap < String , Boolean > vsNameToOutputStructureFields = new TreeMap < String , Boolean >( );
      vsNamesToOutputStructureFields.put( sensorPool.getConfig( ).getName( ) , vsNameToOutputStructureFields );
      for ( DataField fields : sensorPool.getConfig( ).getOutputStructure( ) )
         vsNameToOutputStructureFields.put( fields.getName( ) , Boolean.TRUE );
      vsNameToOutputStructureFields.put( "timed" , Boolean.TRUE );
      vsNameTOVSConfig.put( sensorPool.getConfig( ).getName( ) , sensorPool.getConfig( ) );
      fileNameToVSInstance.put( sensorPool.getConfig( ).getFileName( ) , sensorPool );
      return true;
   }
   
   public static VirtualSensorPool getVSensorInstanceByFileName ( String fileName ) {
      return fileNameToVSInstance.get( fileName );
   }
   
   public static final TreeMap < String , Boolean > getVsNamesToOutputStructureFieldsMapping ( String vsName ) {
      return vsNamesToOutputStructureFields.get( vsName );
   }
   
   public static VSensorConfig getVSensorConfig ( String vSensorName ) {
      if ( vSensorName == null ) return null;
      return vsNameTOVSConfig.get( vSensorName );
   }
   
   public static void removeFilename ( String fileName ) {
      VSensorConfig config = ( fileNameToVSInstance.get( fileName ) ).getConfig( );
      vsNameTOVSConfig.remove( config.getName( ) );
      fileNameToVSInstance.remove( fileName );
   }
   
   public static Long getLastModifiedTime ( String configFileName ) {
      return Long.valueOf( ( fileNameToVSInstance.get( configFileName ) ).getLastModified( ) );
   }
   
   public static String [ ] getAllKnownFileName ( ) {
      return fileNameToVSInstance.keySet( ).toArray( new String [ 0 ] );
   }
   
   public static VSensorConfig getConfigurationObject ( String fileName ) {
      if ( fileName == null ) return null;
      return ( fileNameToVSInstance.get( fileName ) ).getConfig( );
   }
   
   public static ContainerImpl getContainer ( ) {
      return container;
   }
   
   public static Iterator < VSensorConfig > getAllVSensorConfigs ( ) {
      return vsNameTOVSConfig.values( ).iterator( );
   }
   
   public static VirtualSensorPool getVSensorInstanceByVSName ( String vsensorName ) {
      if ( vsensorName == null ) return null;
      VSensorConfig vSensorConfig = vsNameTOVSConfig.get( vsensorName );
      if ( vSensorConfig == null ) return null;
      return getVSensorInstanceByFileName( vSensorConfig.getFileName( ) );
   }
   
}