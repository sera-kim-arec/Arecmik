package kr.arecmik.widget;

import android.content.Context;
import android.graphics.Color;

/** Saved locally; changing appearance never reads or writes calendar data. */
enum WidgetTheme {
    GLASS("glass","#293B31","#667B6B","#6F8175","#AAB6AD","#A16D65","#647E8B","#FFFFFF","#94A497","#355447"),
    LEMON("lemon","#3E4936","#718365","#89927E","#C3C6B8","#AD7C68","#7B91A0","#544A2E","#9FA793","#4D6242"),
    MONO("mono","#363636","#777777","#888888","#C2C2C2","#686868","#686868","#FFFFFF","#A0A0A0","#444444");

    final String key;final int primary,secondary,muted,outside,sunday,saturday,selectedText,done,active;
    WidgetTheme(String key,String primary,String secondary,String muted,String outside,String sunday,String saturday,String selectedText,String done,String active){this.key=key;this.primary=Color.parseColor(primary);this.secondary=Color.parseColor(secondary);this.muted=Color.parseColor(muted);this.outside=Color.parseColor(outside);this.sunday=Color.parseColor(sunday);this.saturday=Color.parseColor(saturday);this.selectedText=Color.parseColor(selectedText);this.done=Color.parseColor(done);this.active=Color.parseColor(active);}
    static WidgetTheme current(Context c){String key=DataStore.prefs(c).getString("theme","glass");for(WidgetTheme theme:values())if(theme.key.equals(key))return theme;return GLASS;}
    int drawable(Context c,String name){int resource=c.getResources().getIdentifier(name+"_"+key,"drawable",c.getPackageName());return resource!=0?resource:c.getResources().getIdentifier(name,"drawable",c.getPackageName());}
}
