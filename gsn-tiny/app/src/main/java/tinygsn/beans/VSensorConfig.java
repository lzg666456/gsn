/**
* Global Sensor Networks (GSN) Source Code
* Copyright (c) 2006-2014, Ecole Polytechnique Federale de Lausanne (EPFL)
*
* This file is part of GSN.
*
* GSN is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* GSN is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with GSN. If not, see <http://www.gnu.org/licenses/>.
*
* File: gsn-tiny/src/tinygsn/beans/VSensorConfig.java
*
* @author Do Ngoc Hoan
*/


package tinygsn.beans;


import java.util.ArrayList;

import tinygsn.model.wrappers.AbstractWrapper;
import android.os.Parcel;
import android.os.Parcelable;


public class VSensorConfig implements Parcelable  {

	
	public int getId() {
		return id;
	}
	public void setId(int id) {
		this.id = id;
	}

	private int id;
	private String name;
	private InputStream inputStream = null;
	private DataField[] outputStructure;
	private String processingClassName;
	private boolean running;

	private String notify_field, notify_condition, notify_action, notify_contact;
	private Double notify_value;
	private boolean save_to_db;

	
	private ArrayList<StreamSource> streamSources = new ArrayList<StreamSource>();


	public VSensorConfig() {}
	
	public VSensorConfig(Parcel source)
	{
		inputStream = new InputStream();
		int idid = Integer.parseInt(source.readString());
		String processingClass = source.readString();
		String vsName = source.readString();
		int nb = Integer.parseInt(source.readString());
		for(int i=0;i<nb;i++){
			String wrapperN = source.readString();
			int windowSize = Integer.parseInt(source.readString());
			int step = Integer.parseInt(source.readString());
			boolean timeBased = Boolean.parseBoolean(source.readString());
			int aggregator = Integer.parseInt(source.readString());
			try {
			    StreamSource ss = new StreamSource(windowSize, step, timeBased, aggregator);
			    AbstractWrapper w = StaticData.getWrapperByName(wrapperN);
				w.registerListener(ss);
				ss.setWrapper(w);
				ss.setInputStream(inputStream);
				streamSources.add(ss);
				inputStream.addStreamSource(ss);
				outputStructure = w.getOutputStructure();
				outputStructure = StaticData.getProcessingClassByVSConfig(this).getOutputStructure(outputStructure);
			}
			catch (Exception e1) {
				e1.printStackTrace();
			}
		}
		boolean runningState = Boolean.parseBoolean(source.readString());
		String notify_field_par = source.readString();
		String notify_condition_par = source.readString();
		Double notify_value_par = Double.parseDouble(source.readString());
		String notify_action_par = source.readString();
		String notify_contact_par = source.readString();
		boolean save_to_db_par = Boolean.parseBoolean(source.readString());
				
		this.id = idid;
		this.name = vsName;
		this.processingClassName = processingClass;
		this.running = runningState;

		this.notify_field = notify_field_par;
		this.notify_condition = notify_condition_par;
		this.notify_value = notify_value_par;
		this.notify_action = notify_action_par;
		this.notify_contact = notify_contact_par;
		this.save_to_db = save_to_db_par;
		
		try {
			inputStream.setVirtualSensor(StaticData.getProcessingClassByVSConfig(this));
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	public VSensorConfig(int id, String processingClass, String vsName,
			ArrayList<StreamSource> ss, boolean running) {

		this.id = id;
		this.name = vsName;
		this.processingClassName = processingClass;
		this.running = running;

		inputStream = new InputStream();
		for (StreamSource s:ss){
			try {
				s.setInputStream(inputStream);
				streamSources.add(s);
				inputStream.addStreamSource(s);
				outputStructure = s.getWrapper().getOutputStructure();
				outputStructure = StaticData.getProcessingClassByVSConfig(this).getOutputStructure(outputStructure);
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
		try {
			inputStream.setVirtualSensor(StaticData.getProcessingClassByVSConfig(this));
		} catch (Exception e) {
			e.printStackTrace();
		}

	}

	public String getProcessingClassName() {
		return processingClassName;
	}

	public void setProcessingClassName(String processingClassName) {
		this.processingClassName = processingClassName;
	}

	public boolean getRunning() {
		return running;
	}

	public void setRunning(boolean running) {
		this.running = running;
	}

	
	/**
	 * @return Returns the inputStreams.
	 */
	public ArrayList<StreamSource> getStreamSource() {
		return streamSources ;
	}

	public String getName() {
		return this.name;
	}


	/**
	 * @return Returns the outputStructure.
	 */
	public DataField[] getOutputStructure() {
		return this.outputStructure;
	}

	/**
	 * @param virtualSensorName
	 *          The name to set.
	 */
	public void setName(final String virtualSensorName) {
		this.name = virtualSensorName;
	}

	/**
	 * @param outputStructure
	 *          The outputStructure to set.
	 */
	public void setOutputStructure(DataField[] outputStructure) {
		this.outputStructure = outputStructure;
	}

	public boolean equals(Object obj) {
		if (obj instanceof VSensorConfig) {
			VSensorConfig vSensorConfig = (VSensorConfig) obj;
			return name.equals(vSensorConfig.getName());
		}
		return false;
	}

	public int hashCode() {
		if (name != null) {
			return name.hashCode();
		}
		else {
			return super.hashCode();
		}
	}


	public String getNotify_field() {
		return notify_field;
	}

	public void setNotify_field(String notify_field) {
		this.notify_field = notify_field;
	}

	public String getNotify_condition() {
		return notify_condition;
	}

	public void setNotify_condition(String notify_condition) {
		this.notify_condition = notify_condition;
	}

	public String getNotify_action() {
		return notify_action;
	}

	public void setNotify_action(String notify_action) {
		this.notify_action = notify_action;
	}

	public String getNotify_contact() {
		return notify_contact;
	}

	public void setNotify_contact(String notify_contact) {
		this.notify_contact = notify_contact;
	}

	public Double getNotify_value() {
		return notify_value;
	}

	public void setNotify_value(Double notify_value) {
		this.notify_value = notify_value;
	}

	public boolean isSave_to_db() {
		return save_to_db;
	}

	public void setSave_to_db(boolean save_to_db) {
		this.save_to_db = save_to_db;
	}

	@Override
	public int describeContents() {
		return 0;
	}

	@Override
	public void writeToParcel(Parcel dest, int flags) {
		dest.writeString(Integer.toString(id));
		dest.writeString(getProcessingClassName());
		dest.writeString(getName());
		dest.writeString(Integer.toString(streamSources.size()));
		for(StreamSource s:streamSources){
			dest.writeString(s.getWrapper().getWrapperName());
			dest.writeString(Integer.toString(s.getWindowSize()));
			dest.writeString(Integer.toString(s.getStep()));
			dest.writeString(Boolean.toString(s.isTimeBased()));
			dest.writeString(Integer.toString(s.getAggregator()));
		}
		dest.writeString(Boolean.toString(getRunning()));
		dest.writeString(getNotify_field());
		dest.writeString(getNotify_condition());
		dest.writeString(Double.toString(getNotify_value()));
		dest.writeString(getNotify_action());
		dest.writeString(getNotify_contact());
		dest.writeString(Boolean.toString(isSave_to_db()));
	}
	public static final Parcelable.Creator<VSensorConfig> CREATOR  = new Creator<VSensorConfig>() {

	    public VSensorConfig createFromParcel(Parcel source) {

	    	VSensorConfig vs = new VSensorConfig(source);
	    	StaticData.addConfig(vs.id, vs);
	    	StaticData.saveNameID(vs.id, vs.getName());
			return vs;
	    }

	    public VSensorConfig[] newArray(int size) {
	        return new VSensorConfig[size];
	    }

	};


	public InputStream getInputStream() {
		return inputStream;
		
	}

}

